"""Create convenient symlink indexes for workspace reports and logs."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from collections.abc import Callable
import json


@dataclass(frozen=True)
class ReportIndexResult:
    """Describe the report links created in an index directory."""

    directory: Path
    links: tuple[Path, ...]


def create_file_index(
    workspace: str | Path,
    filepath: str,
    output: str | Path | None = None,
) -> ReportIndexResult:
    """Create relative symlinks for one file from every submission.

    :param workspace: Initialized grading workspace containing student records.
    :param filepath: Non-empty relative path to resolve from each report
        directory. A configured required student file may instead be resolved
        from the matching submission directory.
    :param output: Directory in which to create the index. When omitted, the
        index is created at ``<workspace>/<filename>-index``.
    :return: The index directory and the links created there.
    :raises ValueError: If filepath is absolute, empty, or escapes its report
        directory.
    :raises FileNotFoundError: If the workspace is not initialized or its
        students directory does not exist.
    :raises FileExistsError: If an index entry would overwrite a real file or
        directory.
    :raises OSError: If a symlink cannot be created or removed.
    """
    relative_path = Path(filepath)
    if not filepath.strip() or relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("Indexed filepath must be a non-empty path relative to each report directory.")
    return _create_index(
        workspace,
        output,
        source_description=f"file '{filepath}'",
        default_directory_name=f"{relative_path.name}-index",
        targets=lambda students_root: _file_targets(students_root, relative_path),
        missing_message="run report first",
    )


def create_report_index(
    workspace: str | Path,
    output: str | Path | None = None,
) -> ReportIndexResult:
    """Create relative symlinks to every generated report in a workspace.

    :param workspace: Initialized grading workspace containing a ``students``
        directory.
    :param output: Directory in which to create the index. When omitted, the
        index is created at ``<workspace>/report-index``.
    :return: The index directory and the links created there.
    :raises FileNotFoundError: If the workspace is not initialized or its
        students directory does not exist.
    :raises FileExistsError: If an index entry would overwrite a real file or
        directory.
    :raises OSError: If a symlink cannot be created or an existing symlink
        cannot be removed.
    """
    return _create_index(
        workspace,
        output,
        source_description="students",
        default_directory_name="report-index",
        targets=_report_targets,
        missing_message="run report first",
    )


def create_runtime_log_index(
    workspace: str | Path,
    output: str | Path | None = None,
) -> ReportIndexResult:
    """Create relative symlinks to every submission runtime log.

    :param workspace: Initialized grading workspace containing student
        directories and their runtime logs.
    :param output: Directory in which to create the index. When omitted, the
        index is created at ``<workspace>/runtime-log-index``.
    :return: The index directory and the links created there.
    :raises FileNotFoundError: If the workspace is not initialized or its
        reports directory does not exist.
    :raises FileExistsError: If an index entry would overwrite a real file or
        directory.
    :raises OSError: If a symlink cannot be created or removed.
    """
    return create_file_index(workspace, "runtime-output.log", output)


def create_buildtime_log_index(
    workspace: str | Path,
    output: str | Path | None = None,
) -> ReportIndexResult:
    """Create relative symlinks to every submission build log.

    :param workspace: Initialized grading workspace containing student
        directories and their build logs.
    :param output: Directory in which to create the index. When omitted, the
        index is created at ``<workspace>/buildtime-log-index``.
    :return: The index directory and the links created there.
    :raises FileNotFoundError: If the workspace is not initialized or its
        reports directory does not exist.
    :raises FileExistsError: If an index entry would overwrite a real file or
        directory.
    :raises OSError: If a symlink cannot be created or removed.
    """
    return create_file_index(workspace, "build-output.log", output)


def _create_index(
    workspace: str | Path,
    output: str | Path | None,
    source_description: str,
    default_directory_name: str,
    targets: Callable[[Path], list[tuple[str, Path]]],
    missing_message: str,
) -> ReportIndexResult:
    """Create an owned symlink index from a workspace source.

    :param workspace: Initialized grading workspace to inspect.
    :param output: Optional destination directory for the symlink index.
    :param source_description: Human-readable name used in validation errors.
    :param default_directory_name: Directory name used when output is omitted.
    :param targets: Callable that returns ``(name, path)`` source entries.
    :param missing_message: Suggested command when source data is absent.
    :return: The index directory and the links created there.
    :raises FileNotFoundError: If the workspace or source directory is absent.
    :raises FileExistsError: If a real index entry would be overwritten.
    :raises OSError: If a symlink cannot be created or removed.
    """
    workspace_root = Path(workspace).expanduser()
    if not (workspace_root / "workspace.json").is_file():
        raise FileNotFoundError(
            f"Workspace '{workspace_root}' is not initialized; run create-workspace first."
        )

    students_root = workspace_root / "students"
    if not students_root.is_dir():
        raise FileNotFoundError(
            f"{source_description.capitalize()} directory '{students_root}' does not exist; "
            f"{missing_message}."
        )

    index_directory = (
        Path(output).expanduser()
        if output is not None
        else workspace_root / default_directory_name
    )
    index_directory.mkdir(parents=True, exist_ok=True)

    # The index directory is owned by this command: stale symlinks are safe to
    # remove, while real files and directories are deliberately preserved.
    for entry in index_directory.iterdir():
        if entry.is_symlink():
            entry.unlink()

    report_targets = targets(students_root)
    links: list[Path] = []
    for name, target in report_targets:
        link_path = index_directory / name
        if link_path.exists() or link_path.is_symlink():
            raise FileExistsError(
                f"Cannot replace existing non-symlink index entry '{link_path}'."
            )
        relative_target = os.path.relpath(target, start=index_directory)
        link_path.symlink_to(relative_target)
        links.append(link_path)

    return ReportIndexResult(index_directory, tuple(links))


def _report_targets(students_root: Path) -> list[tuple[str, Path]]:
    """Return report files that should appear in a report index.

    :param students_root: Workspace students directory.
    :return: Named report paths for index creation.
    """
    report_targets: list[tuple[str, Path]] = []
    for report_path in sorted(students_root.glob("*/report.txt")):
        if report_path.is_file():
            report_targets.append((report_path.parent.name, report_path))
    for filename in ("report-summary.md", "similarity-report.txt"):
        report_path = students_root.parent / filename
        if report_path.is_file():
            report_targets.append((filename, report_path))

    return report_targets


def _submission_log_targets(
    students_root: Path, filename: str
) -> list[tuple[str, Path]]:
    """Return existing per-submission logs with submission names as links.

    :param students_root: Workspace students directory.
    :param filename: Log filename to index.
    :return: Named log paths for index creation.
    """
    return _file_targets(students_root, Path(filename))


def _file_targets(
    students_root: Path, relative_path: Path
) -> list[tuple[str, Path]]:
    """Resolve one requested file for every report and submission.

    :param students_root: Workspace students directory.
    :param relative_path: Path relative to each student directory.
    :return: Submission names and resolved file paths that exist.
    """
    targets: list[tuple[str, Path]] = []
    for student_root in sorted(path for path in students_root.iterdir() if path.is_dir()):
        report_target = student_root / relative_path
        if report_target.is_file():
            targets.append((student_root.name, report_target))
            continue
        metadata_path = student_root / "submission_metadata.json"
        if not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        required_files = metadata.get("required_files", [])
        if isinstance(required_files, list) and relative_path.as_posix() in {
            str(item) for item in required_files if isinstance(item, str)
        }:
            submission_target = student_root / "src-files" / relative_path
            if submission_target.is_file():
                targets.append((student_root.name, submission_target))
    return targets
