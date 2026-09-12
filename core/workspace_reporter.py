"""Generate reports for normalized grading workspaces."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil


@dataclass(frozen=True)
class WorkspaceReportResult:
    """Describe reports generated for one grading workspace."""

    workspace: Path
    reports: tuple[Path, ...]
    summary: Path


class WorkspaceReporter:
    """Prepare build inputs and write reports for imported submissions.

    :param workspace: Initialized grading workspace containing submissions and
        an optional imported teacher template.
    """

    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).expanduser()

    def report(self) -> WorkspaceReportResult:
        """Create build workspaces and one report for each submission.

        :return: Paths to per-submission reports and the summary report.
        :raises FileNotFoundError: If the workspace is not initialized.
        """
        if not (self.workspace / "workspace.json").is_file():
            raise FileNotFoundError(
                f"Workspace '{self.workspace}' is not initialized; run create-workspace first."
            )
        submissions_root = self.workspace / "submissions"
        reports_root = self.workspace / "reports"
        reports_root.mkdir(parents=True, exist_ok=True)
        reports: list[Path] = []
        for submission_root in sorted(path for path in submissions_root.iterdir() if path.is_dir()):
            metadata_path = submission_root / "submission_metadata.json"
            if not metadata_path.is_file():
                continue
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            build_root, teacher_files, replaced_files = self._prepare_build_workspace(
                submission_root, metadata
            )
            report_path = reports_root / submission_root.name / "report.txt"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_report(
                report_path, metadata, build_root, teacher_files, replaced_files
            )
            reports.append(report_path)

        summary = reports_root / "summary.txt"
        summary.write_text(
            f"Workspace: {self.workspace}\n"
            f"Submissions reported: {len(reports)}\n"
            + "\n".join(f"- {path}" for path in reports)
            + "\n",
            encoding="utf-8",
        )
        return WorkspaceReportResult(self.workspace, tuple(reports), summary)

    def _prepare_build_workspace(
        self, submission_root: Path, metadata: dict[str, object]
    ) -> tuple[Path, list[str], list[str]]:
        """Copy the teacher template and overlay one student submission.

        :param submission_root: Student-only normalized submission directory.
        :param metadata: Submission metadata containing the student file list.
        :return: Build directory, copied teacher files, and replaced files.
        """
        build_root = self.workspace / "build-workspaces" / submission_root.name
        if build_root.exists():
            shutil.rmtree(build_root)
        build_root.mkdir(parents=True)
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
        for filename in metadata.get("student_files", metadata.get("files", [])):
            if not isinstance(filename, str):
                continue
            source = submission_root / filename
            target = build_root / filename
            if target.exists():
                replaced_files.append(filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        metadata["build_workspace"] = str(build_root)
        metadata["teacher_files"] = teacher_files
        metadata["replaced_template_files"] = replaced_files
        (submission_root / "submission_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        return build_root, teacher_files, replaced_files

    @staticmethod
    def _write_report(
        report_path: Path,
        metadata: dict[str, object],
        build_root: Path,
        teacher_files: list[str],
        replaced_files: list[str],
    ) -> None:
        """Write an auditable report for one prepared submission.

        :param report_path: Destination report text file.
        :param metadata: Normalized submission metadata.
        :param build_root: Prepared build workspace path.
        :param teacher_files: Teacher files copied into the build workspace.
        :param replaced_files: Teacher files replaced by student files.
        """
        warnings = metadata.get("warnings", [])
        lines = [
            f"Submission: {metadata.get('identifier', report_path.parent.name)}",
            f"Original filename: {metadata.get('original_filename', '')}",
            f"Source archive: {metadata.get('source_archive', '')}",
            f"Student workspace: {report_path.parents[1]}",
            f"Build workspace: {build_root}",
            f"Teacher files copied: {len(teacher_files)}",
            f"Student files overlaid: {len(metadata.get('student_files', metadata.get('files', [])))}",
            f"Template files replaced: {len(replaced_files)}",
            "Warnings:",
        ]
        lines.extend(f"- {warning}" for warning in warnings if isinstance(warning, str))
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
