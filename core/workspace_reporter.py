"""Generate auditable reports for normalized grading workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Callable, Mapping, TypedDict


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

    def report(self) -> WorkspaceReportResult:
        """Prepare, build, run, and report every normalized submission.

        :return: Paths to per-submission reports, the summary, and similarity
            report.
        :raises FileNotFoundError: If the workspace is not initialized.
        :raises ValueError: If the runtime timeout is not positive.
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
        reports_root = self.workspace / "reports"
        reports_root.mkdir(parents=True, exist_ok=True)
        run_time = datetime.now(timezone.utc).isoformat()
        reports: list[Path] = []
        submissions_root = self.workspace / "submissions"
        if submissions_root.is_dir():
            submission_roots = sorted(
                path for path in submissions_root.iterdir() if path.is_dir()
            )
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
                        f"Reporting {index}/{total} {submission_root.name}: {status}",
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
                print(
                    f"Reporting {index}/{total} {submission_root.name}: "
                    f"build={outcome['build_status']} "
                    f"runtime={outcome['runtime_status']} "
                    f"report={report_path}",
                    flush=True,
                )

        summary = reports_root / "summary.txt"
        summary.write_text(
            f"Workspace path prefix: {self.workspace}\n"
            f"Run time (UTC): {run_time}\n"
            f"Submissions reported: {len(reports)}\n"
            + "\n".join(
                f"- {self._display_workspace_path(path)}" for path in reports
            )
            + "\n",
            encoding="utf-8",
        )
        similarity_report = self._write_similarity_report(reports_root, run_time)
        return WorkspaceReportResult(
            self.workspace, tuple(reports), summary, similarity_report
        )

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
        legacy_details = self._collect_legacy_details(build_root)
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
        self, build_root: Path
    ) -> dict[str, object]:
        """Collect the detailed sections from the legacy report style.

        :param build_root: Prepared source tree for one submission.
        :return: Serializable header, method, and check details.
        """
        configuration = self._load_rule_configuration()
        source_files = sorted(
            path for path in build_root.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}
            and "build" not in path.parts
        )
        headers: list[str] = []
        for source_file in source_files:
            source_lines = source_file.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            first_nonempty = next((line.strip() for line in source_lines if line.strip()), "")
            status = "FOUND" if first_nonempty.startswith(("//", "/*", "*")) else "MISSING"
            headers.append(
                f"{status} header comment: {source_file.relative_to(build_root)}"
            )

        methods: dict[str, list[str]] = {}
        configured_methods = configuration.get("methods", {})
        source_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace") for path in source_files
        )
        if isinstance(configured_methods, Mapping):
            for clazz, class_methods in configured_methods.items():
                if not isinstance(clazz, str) or not isinstance(class_methods, Mapping):
                    continue
                results: list[str] = []
                for method_name in class_methods:
                    if not isinstance(method_name, str):
                        continue
                    qualified = f"{clazz}::{method_name}"
                    status = "FOUND" if qualified in source_text else "MISSING"
                    results.append(f"{status}: {qualified}")
                methods[clazz] = results

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
            f"Run time (UTC): {metadata.get('last_reported_at', '')}", "",
            "Criteria", "--------",
        ]
        for criterion in criteria:
            lines.append(
                f"[{criterion['status']}] {criterion['id']} "
                f"(automated={criterion['automated']}): {criterion['evidence']}"
            )
        lines.extend(["", "File Headers", "------------"])
        lines.extend(str(item) for item in legacy_details["headers"])
        lines.extend(["", "Methods", "-------"])
        methods = legacy_details["methods"]
        assert isinstance(methods, dict)
        for clazz, method_results in methods.items():
            lines.append(f"{clazz}:")
            lines.extend(f"  {result}" for result in method_results)
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

    def _write_similarity_report(self, reports_root: Path, run_time: str) -> Path:
        """Write a separate cohort similarity-analysis status report.

        :param reports_root: Workspace report output directory.
        :param run_time: UTC timestamp shared by this reporting run.
        :return: Similarity report path.
        """
        path = reports_root / "similarity-report.txt"
        path.write_text(
            "Similarity report\n=================\n"
            f"Run time (UTC): {run_time}\nStatus: not run\n"
            "Reason: no instructor-provided CodeAnalyzer was found in this workspace.\n"
            "No similarity score or academic-integrity finding was assigned.\n",
            encoding="utf-8",
        )
        return path
