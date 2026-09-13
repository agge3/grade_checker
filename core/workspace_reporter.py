"""Generate auditable reports for normalized grading workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from typing import Callable, Mapping, TypedDict

from core.similarity import SimilarityAnalyzer


class CriterionResult(TypedDict):
    """Describe the result and evidence for one report criterion."""

    id: str
    status: str
    evidence: str
    automated: bool


@dataclass(frozen=True)
class WorkspaceReportResult:
    """Describe reports generated for one grading workspace."""

    workspace: Path
    reports: tuple[Path, ...]
    summary: Path
    similarity_report: Path


class WorkspaceReporter:
    """Build and report on every normalized submission in a workspace.

    :param workspace: Initialized grading workspace containing submissions and
        an optional imported teacher template.
    :param runtime_timeout: Maximum seconds allowed for one student program.
    """

    def __init__(self, workspace: str | Path, runtime_timeout: int = 30) -> None:
        self.workspace = Path(workspace).expanduser()
        self.runtime_timeout = runtime_timeout
        self.rule_configuration = "workspace metadata"
        self.code_analyzer_path: Path | None = None
        self.disable_code_analyzer = False

    def report(
        self, submission: str | Sequence[str] | None = None
    ) -> WorkspaceReportResult:
        """Prepare, build, run, and report every normalized submission.

        :param submission: Optional normalized submission identifier or
            identifiers. When provided, only those submissions are reported.
        :return: Paths to per-submission reports, the summary, and similarity
            report.
        :raises FileNotFoundError: If the workspace is not initialized.
        :raises ValueError: If the runtime timeout is not positive or the
            selected submission identifier is invalid.
        """
        if self.runtime_timeout <= 0:
            raise ValueError("Runtime timeout must be positive.")
        if not (self.workspace / "workspace.json").is_file():
            raise FileNotFoundError(
                f"Workspace '{self.workspace}' is not initialized; run create-workspace first."
            )
        workspace_metadata = json.loads(
            (self.workspace / "workspace.json").read_text(encoding="utf-8")
        )
        self.rule_configuration = str(
            workspace_metadata.get("milestone_configuration")
            or workspace_metadata.get("milestone")
            or "workspace metadata"
        )
        configured_analyzer = workspace_metadata.get("code_analyzer")
        if isinstance(configured_analyzer, str) and configured_analyzer:
            self.code_analyzer_path = Path(configured_analyzer).expanduser()
        elif not self.disable_code_analyzer and self.code_analyzer_path is None:
            self.code_analyzer_path = self._find_repository_analyzer()
            if self.code_analyzer_path is not None:
                print(f"Default CodeAnalyzer found at: {self.code_analyzer_path}")
        reports_root = self.workspace / "reports"
        reports_root.mkdir(parents=True, exist_ok=True)
        local_now = datetime.now().astimezone().replace(microsecond=0)
        timezone_name = local_now.tzname() or "local"
        run_time = (
            f"{local_now.strftime('%Y-%m-%d %H:%M:%S')} ({timezone_name})"
        )
        reports: list[Path] = []
        summary_rows: list[dict[str, object]] = []
        submissions_root = self.workspace / "submissions"
        selected_submissions = (
            [submission] if isinstance(submission, str) else list(submission or [])
        )
        if selected_submissions and not submissions_root.is_dir():
            raise ValueError(
                "Unknown submission selection: the workspace has no submissions."
            )
        if submissions_root.is_dir():
            available_submission_roots = sorted(
                path for path in submissions_root.iterdir() if path.is_dir()
            )
            if not selected_submissions:
                submission_roots = available_submission_roots
            else:
                unavailable = [
                    name for name in selected_submissions
                    if submissions_root / name not in available_submission_roots
                ]
                if unavailable:
                    available = ", ".join(
                        path.name for path in available_submission_roots
                    ) or "none"
                    raise ValueError(
                        f"Unknown submission(s) {unavailable}. Available submissions: {available}."
                    )
                submission_roots = [
                    submissions_root / name for name in selected_submissions
                ]
            total = len(submission_roots)
            for index, submission_root in enumerate(submission_roots, start=1):
                metadata_path = submission_root / "submission_metadata.json"
                if not metadata_path.is_file():
                    continue
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                def update_status(status: str) -> None:
                    """Show the active phase for the current submission.

                    :param status: Short phase description displayed in the
                        progress line.
                    """
                    print(
                        f"Reporting {index}/{total} {submission_root.name}: "
                        f"{self._colorize(status, 'cyan')}",
                        end="\r",
                        flush=True,
                    )

                update_status("preparing")
                outcome = self._process_submission(
                    submission_root, metadata, run_time, update_status
                )
                report_path = reports_root / submission_root.name / "report.txt"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                self._write_report(report_path, outcome)
                reports.append(report_path)
                legacy_details = outcome["legacy_details"]
                assert isinstance(legacy_details, dict)
                student_files = metadata.get("student_files", metadata.get("files", []))
                summary_rows.append({
                    "submission": submission_root.name,
                    "submission_status": self._submission_status(metadata),
                    "build_status": outcome["build_status"],
                    "runtime_status": outcome["runtime_status"],
                    "methods_found": legacy_details["methods_found"],
                    "methods_expected": legacy_details["methods_expected"],
                    "required_files_found": self._required_files_found(metadata),
                    "required_files_expected": self._required_files_expected(metadata),
                    "method_headers_found": legacy_details["method_headers_found"],
                    "method_headers_expected": legacy_details["method_headers_expected"],
                })
                print(
                    f"Reporting {index}/{total} {submission_root.name}: "
                    f"build={self._colorize_status(str(outcome['build_status']))} "
                    f"runtime={self._colorize_status(str(outcome['runtime_status']))} "
                    f"report={self._colorize(self._display_workspace_path(report_path), 'blue')}",
                    flush=True,
                )

        summary = reports_root / "summary.md"
        summary.write_text(self._write_summary(summary_rows, run_time), encoding="utf-8")
        similarity_report = self._write_similarity_report(
            reports_root, submissions_root, run_time
        )
        return WorkspaceReportResult(
            self.workspace, tuple(reports), summary, similarity_report
        )

    @staticmethod
    def _submission_status(metadata: dict[str, object]) -> str:
        """Determine the high-level status of an imported submission.

        :param metadata: Submission metadata containing files and warnings.
        :return: ``pass``, ``warning``, or ``missing``.
        """
        student_files = metadata.get("student_files", metadata.get("files", []))
        if not isinstance(student_files, list) or not student_files:
            return "missing"
        return "warning" if metadata.get("warnings") else "pass"

    @staticmethod
    def _find_repository_analyzer() -> Path | None:
        """Find an optional CodeAnalyzer in the grader repository root.

        :return: Existing analyzer directory or source path, or ``None`` when
            the optional analyzer is not installed.
        """
        repository_root = Path(__file__).resolve().parents[1]
        candidates = (
            repository_root / "CodeAnalyzer",
            repository_root / "CodeAnalyzer.cpp",
        )
        for candidate in candidates:
            if candidate.is_dir() and (candidate / "CodeAnalyzer.cpp").is_file():
                return candidate
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _required_files_found(metadata: dict[str, object]) -> int:
        """Count configured required files present in a submission.

        :param metadata: Submission metadata containing expected and copied
            file names.
        :return: Number of required files found.
        """
        student_files = metadata.get("student_files", metadata.get("files", []))
        if not isinstance(student_files, list):
            return 0
        required_files = metadata.get("required_files")
        if not isinstance(required_files, list) or not required_files:
            return len(student_files)
        return sum(
            isinstance(required, str) and required in student_files
            for required in required_files
        )

    @staticmethod
    def _required_files_expected(metadata: dict[str, object]) -> int:
        """Count configured required files for a submission.

        :param metadata: Submission metadata containing expected file names.
        :return: Number of required files expected.
        """
        required_files = metadata.get("required_files")
        if isinstance(required_files, list) and required_files:
            return len(required_files)
        student_files = metadata.get("student_files", metadata.get("files", []))
        return len(student_files) if isinstance(student_files, list) else 0

    def _write_summary(
        self, rows: list[dict[str, object]], run_time: str
    ) -> str:
        """Build the Markdown summary table for a reporting run.

        :param rows: Per-submission status and grading counts.
        :param run_time: Local timestamp for this reporting run.
        :return: Markdown document content.
        """
        expected = rows[0] if rows else {}
        headers = [
            "Submission", "Submission status", "Build status", "Runtime status",
            f"Methods found (expected: {expected.get('methods_expected', 0)})",
            f"Required files found (expected: {expected.get('required_files_expected', 0)})",
            f"Method headers found (expected: {expected.get('method_headers_expected', 0)})",
        ]
        table_rows = [
            [
                str(row["submission"]),
                self._summary_status(str(row["submission_status"])),
                self._summary_status(str(row["build_status"])),
                self._summary_status(str(row["runtime_status"])),
                str(row["methods_found"]), str(row["required_files_found"]),
                str(row["method_headers_found"]),
            ]
            for row in rows
        ]
        widths = [
            max([len(headers[index])] + [len(row[index]) for row in table_rows])
            for index in range(len(headers))
        ]
        format_row = lambda values: "| " + " | ".join(
            value.ljust(widths[index]) for index, value in enumerate(values)
        ) + " |"
        separator = "| " + " | ".join(
            "-" * max(3, width) for width in widths
        ) + " |"
        lines = [
            "# Grading Summary", "",
            f"Workspace path prefix: `{self.workspace}`  ",
            f"Ran at: {run_time}  ",
            f"Submissions reported: {len(rows)}", "",
            format_row(headers), separator,
            *(format_row(row) for row in table_rows),
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _summary_status(status: str) -> str:
        """Add a portable colored indicator to a Markdown status value.

        :param status: Grading status to display in the summary table.
        :return: Status prefixed with a colored Unicode indicator.
        """
        indicator = {
            "pass": "✅", "fail": "❌", "warning": "⚠️", "skipped": "⚠️",
        }.get(status, "ℹ️")
        return f"{indicator} {status}"

    def _display_workspace_path(self, path: Path) -> str:
        """Render a workspace path relative to the reported workspace root.

        :param path: Path located inside this workspace.
        :return: Short path with a ``<workspace-path>/`` prefix hint, or the
            original path when it is outside the workspace.
        """
        try:
            return f"<workspace-path>/{path.relative_to(self.workspace).as_posix()}"
        except ValueError:
            return str(path)

    @staticmethod
    def _colorize(text: str, color: str) -> str:
        """Apply a terminal color when output is an interactive terminal.

        :param text: Console text to format.
        :param color: ANSI color name supported by this reporter.
        :return: Colored text for interactive output, otherwise unchanged text.
        """
        if not os.environ.get("NO_COLOR") and sys.stdout.isatty():
            colors = {
                "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
                "blue": "\033[34m", "cyan": "\033[36m",
            }
            prefix = colors.get(color)
            if prefix:
                return f"{prefix}{text}\033[0m"
        return text

    @classmethod
    def _colorize_status(cls, status: str) -> str:
        """Color a grading status according to its outcome.

        :param status: Build or runtime status to display.
        :return: Colorized status when supported by the terminal.
        """
        color = {
            "pass": "green", "fail": "red", "warning": "yellow",
            "skipped": "yellow", "manual_review": "yellow",
        }.get(status, "cyan")
        return cls._colorize(status, color)

    def _process_submission(
        self,
        submission_root: Path,
        metadata: dict[str, object],
        run_time: str,
        update_status: Callable[[str], None],
    ) -> dict[str, object]:
        """Prepare and evaluate one submission without stopping the cohort.

        :param submission_root: Student-only normalized submission directory.
        :param metadata: Submission metadata loaded from disk.
        :param run_time: UTC timestamp shared by this reporting run.
        :param update_status: Callback used to show the active reporting phase.
        :return: Report data including criteria, paths, and diagnostics.
        """
        report_root = self.workspace / "reports" / submission_root.name
        report_root.mkdir(parents=True, exist_ok=True)
        update_status("preparing build workspace")
        build_root, teacher_files, replaced_files = self._prepare_build_workspace(
            submission_root, metadata
        )
        build_log = report_root / "build-output.log"
        runtime_log = report_root / "runtime-output.log"
        update_status("building")
        build_status, build_output, executable = self._build(build_root)
        build_log.write_text(build_output, encoding="utf-8")
        update_status("running")
        runtime_status, runtime_output = self._run(build_root, executable, build_status)
        runtime_log.write_text(runtime_output, encoding="utf-8")
        legacy_details = self._collect_legacy_details(
            build_root, metadata.get("student_files", metadata.get("files", []))
        )
        student_files = metadata.get("student_files", metadata.get("files", []))
        criteria: list[CriterionResult] = [
            {
                "id": "submission.files",
                "status": "pass" if isinstance(student_files, list) and student_files else "manual_review",
                "evidence": f"Student files: {student_files}",
                "automated": True,
            },
            {
                "id": "build.success",
                "status": build_status,
                "evidence": self._display_workspace_path(build_log),
                "automated": True,
            },
            {
                "id": "runtime.execution",
                "status": runtime_status,
                "evidence": self._display_workspace_path(runtime_log),
                "automated": True,
            },
            {
                "id": "manual.review",
                "status": "manual_review",
                "evidence": "Review notes.md and overrides.json.",
                "automated": False,
            },
        ]
        if metadata.get("warnings"):
            criteria.append({
                "id": "submission.warnings",
                "status": "warning",
                "evidence": str(metadata["warnings"]),
                "automated": True,
            })
        metadata.update({
            "build_workspace": str(build_root),
            "teacher_files": teacher_files,
            "replaced_template_files": replaced_files,
            "last_reported_at": run_time,
            "build_log": str(build_log),
            "runtime_log": str(runtime_log),
            "criteria": criteria,
            "rule_configuration": self.rule_configuration,
        })
        update_status("writing report")
        (submission_root / "submission_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        self._initialize_notes(report_root / "notes.md")
        overrides = report_root / "overrides.json"
        if not overrides.exists():
            overrides.write_text("{}\n", encoding="utf-8")
        return {
            "metadata": metadata,
            "workspace_root": self.workspace,
            "student_root": submission_root,
            "build_root": build_root,
            "build_status": build_status,
            "runtime_status": runtime_status,
            "build_log": build_log,
            "runtime_log": runtime_log,
            "criteria": criteria,
            "legacy_details": legacy_details,
        }

    def _collect_legacy_details(
        self, build_root: Path, student_files_value: object
    ) -> dict[str, object]:
        """Collect the detailed sections from the legacy report style.

        :param build_root: Prepared source tree for one submission.
        :param student_files_value: Student-provided file names from submission
            metadata; only these files are checked for headers and methods.
        :return: Serializable header, method, and check details.
        """
        configuration = self._load_rule_configuration()
        source_files = sorted(
            path for path in build_root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}
            and "build" not in path.parts
        )
        student_files = (
            {name for name in student_files_value if isinstance(name, str)}
            if isinstance(student_files_value, list)
            else set()
        )
        student_source_files = [
            path for path in source_files
            if path.relative_to(build_root).as_posix() in student_files
            or path.name in student_files
        ]
        headers: list[str] = []
        for source_file in student_source_files:
            header_content = self._file_header_content(source_file)
            relative_path = source_file.relative_to(build_root)
            if header_content is None:
                headers.append(f"MISSING header comment: {relative_path}")
            else:
                headers.append(
                    f"FOUND header comment: {relative_path}\n{header_content}"
                )

        methods: dict[str, list[str]] = {}
        method_headers: dict[str, list[str]] = {}
        configured_methods = configuration.get("methods", {})
        source_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in student_source_files
        )
        if isinstance(configured_methods, Mapping):
            for clazz, class_methods in configured_methods.items():
                if not isinstance(clazz, str) or not isinstance(class_methods, Mapping):
                    continue
                results: list[str] = []
                header_results: list[str] = []
                for method_name in class_methods:
                    if not isinstance(method_name, str):
                        continue
                    qualified = f"{clazz}::{method_name}"
                    status = "FOUND" if qualified in source_text else "MISSING"
                    results.append(f"{status}: {qualified}")
                    header_content = self._method_header_content(
                        student_source_files, clazz, method_name
                    )
                    if header_content is None:
                        header_results.append(f"MISSING method header: {qualified}")
                    else:
                        header_results.append(
                            f"FOUND method header: {qualified}\n{header_content}"
                        )
                methods[clazz] = results
                method_headers[clazz] = header_results

        extra_credit = configuration.get("extra_credit", {})
        if isinstance(extra_credit, Mapping) and extra_credit.get("enabled"):
            gtest_check = (
                "Configured legacy check (not executed by workspace reporter): "
                f"{extra_credit.get('args', [])}"
            )
        else:
            gtest_check = "No extra-credit/GTest check configured."
        options = configuration.get("options", {})
        output_check = (
            "Configured; inspect captured build output."
            if isinstance(options, Mapping) and options.get("check_build")
            else "No output-check rule configured."
        )
        return {
            "headers": headers or ["No C/C++ source files found."],
            "methods": methods or {"(no configured methods)": ["Needs manual review."]},
            "method_headers": method_headers or {
                "(no configured methods)": ["Needs manual review."]
            },
            "methods_found": sum(
                str(result).startswith("FOUND")
                for results in methods.values() for result in results
            ),
            "methods_expected": sum(len(results) for results in methods.values()),
            "method_headers_found": sum(
                str(result).startswith("FOUND")
                for results in method_headers.values() for result in results
            ),
            "method_headers_expected": sum(
                len(results) for results in method_headers.values()
            ),
            "gtest_check": gtest_check,
            "output_check": output_check,
        }

    def _load_rule_configuration(self) -> dict[str, object]:
        """Load the milestone configuration associated with this workspace.

        :return: Configuration mapping, or an empty mapping when unavailable.
        """
        metadata = json.loads(
            (self.workspace / "workspace.json").read_text(encoding="utf-8")
        )
        configuration_path = metadata.get("milestone_configuration")
        if not isinstance(configuration_path, str) or not configuration_path:
            return {}
        path = Path(configuration_path).expanduser()
        if not path.is_file():
            candidate = self.workspace.parent / path
            path = candidate if candidate.is_file() else path
        if not path.is_file():
            return {}
        configuration = json.loads(path.read_text(encoding="utf-8"))
        return configuration if isinstance(configuration, dict) else {}

    @staticmethod
    def _method_header_content(
        source_files: list[Path], clazz: str, method_name: str
    ) -> str | None:
        """Return the preceding documentation for a method implementation.

        :param source_files: C/C++ source files to inspect.
        :param clazz: Class containing the configured method.
        :param method_name: Method name to locate.
        :return: Comment content when a matching implementation is documented,
            otherwise ``None``.
        """
        pattern = re.compile(
            rf"\b(?:{re.escape(clazz)}\s*::\s*)?{re.escape(method_name)}\s*\("
        )
        for source_file in source_files:
            lines = source_file.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            for index, line in enumerate(lines):
                if not pattern.search(line):
                    continue
                previous = index - 1
                while previous >= 0 and not lines[previous].strip():
                    previous -= 1
                if previous < 0:
                    continue
                if lines[previous].strip().startswith("//"):
                    return lines[previous].strip()
                if "*/" in lines[previous]:
                    comment_lines = [lines[previous].strip()]
                    cursor = previous - 1
                    while cursor >= 0:
                        comment_lines.append(lines[cursor].strip())
                        if "/*" in lines[cursor]:
                            break
                        cursor -= 1
                    return "\n".join(reversed(comment_lines))
                if lines[previous].strip().startswith("*"):
                    comment_lines = [lines[previous].strip()]
                    cursor = previous - 1
                    while cursor >= 0:
                        comment_lines.append(lines[cursor].strip())
                        if "/*" in lines[cursor]:
                            break
                        cursor -= 1
                    return "\n".join(reversed(comment_lines))
        return None

    @staticmethod
    def _file_header_content(source_file: Path) -> str | None:
        """Return the leading documentation comment from a source file.

        :param source_file: C or C++ source file to inspect.
        :return: Preserved multiline header comment, or ``None`` when the file
            has no leading comment.
        """
        lines = source_file.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        first = next((index for index, line in enumerate(lines) if line.strip()), None)
        if first is None:
            return None
        first_line = lines[first].strip()
        if first_line.startswith("//"):
            comment_lines: list[str] = []
            for line in lines[first:]:
                if not line.strip().startswith("//"):
                    break
                comment_lines.append(line.strip())
            return "\n".join(comment_lines)
        if first_line.startswith("/*"):
            comment_lines = []
            for line in lines[first:]:
                comment_lines.append(line.strip())
                if "*/" in line:
                    return "\n".join(comment_lines)
            return None
        return None

    @staticmethod
    def _initialize_notes(notes_path: Path) -> None:
        """Create a guided TA-notes file without overwriting existing notes.

        :param notes_path: Destination for the per-submission TA notes.
        """
        if notes_path.exists():
            return
        notes_path.write_text(
            "# TA Notes\n\n"
            "Use this file for human review notes, explanations, and decisions "
            "about this submission.\n\n"
            "This is different from `report.txt`: the report is generated by "
            "the application and records automated results, evidence, and logs. "
            "Do not edit the report to record manual grading decisions.\n\n"
            "Examples:\n\n"
            "- Explain a manual interpretation of a rubric criterion.\n"
            "- Record a student clarification or a manual repair.\n"
            "- Note what should be rechecked after a resubmission.\n\n"
            "For structured corrections to automated findings, use `overrides.json`.\n",
            encoding="utf-8",
        )

    def _prepare_build_workspace(
        self, submission_root: Path, metadata: dict[str, object]
    ) -> tuple[Path, list[str], list[str]]:
        """Copy the teacher template and overlay one student submission.

        :param submission_root: Student-only normalized submission directory.
        :param metadata: Submission metadata containing student file names.
        :return: Build directory, copied teacher files, and replaced files.
        """
        build_root = self.workspace / "build-workspaces" / submission_root.name
        if build_root.exists():
            shutil.rmtree(build_root)
        build_root.mkdir(parents=True, exist_ok=True)
        template_root = self.workspace / "references" / "template"
        teacher_files: list[str] = []
        replaced_files: list[str] = []
        if template_root.is_dir():
            for source in sorted(path for path in template_root.rglob("*") if path.is_file()):
                relative = source.relative_to(template_root)
                target = build_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                teacher_files.append(relative.as_posix())
        else:
            metadata.setdefault("warnings", [])
            if isinstance(metadata["warnings"], list):
                metadata["warnings"].append("teacher template is not imported")
        student_files = metadata.get("student_files", metadata.get("files", []))
        if isinstance(student_files, list):
            for filename in student_files:
                if not isinstance(filename, str):
                    continue
                source = submission_root / filename
                target = build_root / filename
                if target.exists():
                    replaced_files.append(filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        return build_root, teacher_files, replaced_files

    def _build(self, build_root: Path) -> tuple[str, str, Path | None]:
        """Configure and build one prepared C++ workspace.

        :param build_root: Prepared build workspace containing the template and
            student files.
        :return: Status, combined build diagnostics, and executable path.
        """
        cmake_file = build_root / "CMakeLists.txt"
        if not cmake_file.is_file():
            return "skipped", "Build skipped: CMakeLists.txt was not found.\n", None
        build_dir = build_root / "build"
        lines = [f"Source directory: {build_root}\n", f"Build directory: {build_dir}\n"]
        try:
            configure = subprocess.run(
                ["cmake", "-S", str(build_root), "-B", str(build_dir)],
                capture_output=True, text=True, timeout=120, check=False,
            )
            lines.extend(["$ cmake configure\n", configure.stdout, configure.stderr])
            if configure.returncode != 0:
                return "fail", "".join(lines), None
            build = subprocess.run(
                ["cmake", "--build", str(build_dir)],
                capture_output=True, text=True, timeout=120, check=False,
            )
            lines.extend(["$ cmake --build\n", build.stdout, build.stderr])
            if build.returncode != 0:
                return "fail", "".join(lines), None
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            lines.append(f"Build failed: {error}\n")
            return "fail", "".join(lines), None
        executable = self._find_executable(cmake_file, build_dir)
        return "pass", "".join(lines), executable

    def _run(
        self, build_root: Path, executable: Path | None, build_status: str
    ) -> tuple[str, str]:
        """Run a successfully built student program with a timeout.

        :param build_root: Prepared build workspace.
        :param executable: Executable selected from the CMake target.
        :param build_status: Result of the build criterion.
        :return: Runtime status and runtime-only diagnostics.
        """
        if build_status != "pass":
            return "skipped", "Runtime skipped because the build did not pass.\n"
        if executable is None:
            return "skipped", "Runtime skipped: executable target was not found.\n"
        try:
            result = subprocess.run(
                [str(executable)], cwd=build_root, capture_output=True, text=True,
                timeout=self.runtime_timeout, check=False,
            )
        except subprocess.TimeoutExpired as error:
            return "fail", f"Runtime timed out after {self.runtime_timeout} seconds.\n{error}\n"
        except OSError as error:
            return "fail", f"Runtime could not start: {error}\n"
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        output += f"\n[exit status: {result.returncode}]\n"
        return ("pass" if result.returncode == 0 else "fail"), output

    @staticmethod
    def _find_executable(cmake_file: Path, build_dir: Path) -> Path | None:
        """Find the first CMake executable target in the build directory.

        :param cmake_file: CMake project file containing target declarations.
        :param build_dir: Directory containing built artifacts.
        :return: Existing executable path, if one can be identified.
        """
        contents = cmake_file.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"add_executable\s*\(\s*([A-Za-z0-9_.+-]+)", contents)
        if match is None:
            return None
        target_name = match.group(1)
        candidates = [path for path in build_dir.rglob("*") if path.is_file() and path.name == target_name]
        if not candidates:
            candidates = [path for path in build_dir.rglob("*") if path.is_file() and path.stem == target_name]
        return sorted(candidates)[0] if candidates else None

    @staticmethod
    def _write_report(report_path: Path, outcome: dict[str, object]) -> None:
        """Write a sectioned plain-text report with criterion evidence.

        :param report_path: Destination report text file.
        :param outcome: Report data for one submission.
        """
        metadata = outcome["metadata"]
        assert isinstance(metadata, dict)
        criteria = outcome["criteria"]
        assert isinstance(criteria, list)
        legacy_details = outcome["legacy_details"]
        assert isinstance(legacy_details, dict)
        lines = [
            "Submission report", "=================",
            f"Workspace path prefix: {outcome['workspace_root']}",
            f"Submission identifier: {metadata.get('identifier', report_path.parent.name)}",
            f"Original filename: {metadata.get('original_filename', '')}",
            f"Source archive: {metadata.get('source_archive', '')}",
            f"Student workspace: {WorkspaceReporter._display_report_path(outcome['workspace_root'], outcome['student_root'])}",
            f"Build workspace: {WorkspaceReporter._display_report_path(outcome['workspace_root'], outcome['build_root'])}",
            f"Rule/configuration: {metadata.get('rule_configuration', 'workspace metadata')}",
            f"Ran at: {metadata.get('last_reported_at', '')}", "",
            "Criteria", "--------",
        ]
        for criterion in criteria:
            lines.append(
                f"[{criterion['status']}] {criterion['id']} "
                f"(automated={criterion['automated']}): {criterion['evidence']}"
            )
        lines.extend(["", "File Headers", "------------"])
        headers = legacy_details["headers"]
        assert isinstance(headers, list)
        for index, item in enumerate(headers, start=1):
            item_lines = str(item).splitlines()
            lines.append(f"{index}. {item_lines[0]}")
            lines.extend(f"     {line}" for line in item_lines[1:])
        header_found = sum(str(item).startswith("FOUND") for item in headers)
        header_missing = sum(str(item).startswith("MISSING") for item in headers)
        lines.append(
            f"Summary: {header_found} found, {header_missing} missing."
        )
        lines.extend(["", "Methods", "-------"])
        methods = legacy_details["methods"]
        assert isinstance(methods, dict)
        for clazz, method_results in methods.items():
            lines.append(f"{clazz}:")
            found = sum(str(result).startswith("FOUND") for result in method_results)
            missing = sum(str(result).startswith("MISSING") for result in method_results)
            lines.extend(
                f"  {index}. {result}"
                for index, result in enumerate(method_results, start=1)
            )
            lines.append(f"  Summary: {found} found, {missing} missing.")
        lines.extend(["", "Method Headers", "---------------"])
        method_headers = legacy_details["method_headers"]
        assert isinstance(method_headers, dict)
        all_header_results: list[object] = []
        for clazz, header_results in method_headers.items():
            lines.append(f"{clazz}:")
            all_header_results.extend(header_results)
            for index, result in enumerate(header_results, start=1):
                result_lines = str(result).splitlines()
                lines.append(f"  {index}. {result_lines[0]}")
                lines.extend(f"     {line}" for line in result_lines[1:])
            found = sum(str(result).startswith("FOUND") for result in header_results)
            missing = sum(str(result).startswith("MISSING") for result in header_results)
            lines.append(f"  Summary: {found} found, {missing} missing.")
        header_found = sum(str(result).startswith("FOUND") for result in all_header_results)
        header_missing = sum(str(result).startswith("MISSING") for result in all_header_results)
        lines.append(
            f"Overall method-header summary: {header_found} found, "
            f"{header_missing} missing."
        )
        lines.extend([
            "", "GTest Check", "-----------", str(legacy_details["gtest_check"]),
            "", "Output Check", "------------", str(legacy_details["output_check"]),
            "", f"Build log: {WorkspaceReporter._display_report_path(outcome['workspace_root'], outcome['build_log'])}",
            f"Runtime log: {WorkspaceReporter._display_report_path(outcome['workspace_root'], outcome['runtime_log'])}",
            f"TA notes: {WorkspaceReporter._display_report_path(outcome['workspace_root'], report_path.parent / 'notes.md')}",
            f"TA overrides: {WorkspaceReporter._display_report_path(outcome['workspace_root'], report_path.parent / 'overrides.json')}",
        ])
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _display_report_path(workspace_root: Path, path: Path) -> str:
        """Render a report path using the report's workspace prefix hint.

        :param workspace_root: Absolute workspace root shown in the report.
        :param path: Path to render.
        :return: Workspace-relative display path, or the original path when it
            is outside the workspace.
        """
        try:
            return f"<workspace-path>/{path.relative_to(workspace_root).as_posix()}"
        except ValueError:
            return str(path)

    def _write_similarity_report(
        self, reports_root: Path, submissions_root: Path, run_time: str
    ) -> Path:
        """Write a separate cohort similarity-analysis status report.

        :param reports_root: Workspace report output directory.
        :param run_time: UTC timestamp shared by this reporting run.
        :return: Similarity report path.
        """
        path = reports_root / "similarity-report.txt"
        if self.code_analyzer_path is None:
            content = (
                "Similarity report\n=================\n"
                f"Ran at: {run_time}\nStatus: not run\n"
                "Reason: no CodeAnalyzer path was configured.\n"
                "No similarity score or academic-integrity finding was assigned.\n"
            )
        else:
            try:
                analyzer = SimilarityAnalyzer(self.code_analyzer_path)
                content = (
                    "Similarity report\n=================\n"
                    f"Ran at: {run_time}\nStatus: complete\n"
                    + analyzer.run(submissions_root, path)
                )
            except (FileNotFoundError, RuntimeError, ValueError) as error:
                content = (
                    "Similarity report\n=================\n"
                    f"Ran at: {run_time}\nStatus: failed\n"
                    f"Reason: {error}\n"
                    "No similarity score or academic-integrity finding was assigned.\n"
                )
        path.write_text(content, encoding="utf-8")
        return path
