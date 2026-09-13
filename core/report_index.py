"""Create a convenient symlink index for workspace reports."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class ReportIndexResult:
    """Describe the report links created in an index directory."""

    directory: Path
    links: tuple[Path, ...]


def create_report_index(
    workspace: str | Path,
    output: str | Path | None = None,
) -> ReportIndexResult:
    """Create relative symlinks to every generated report in a workspace.

    :param workspace: Initialized grading workspace containing a ``reports``
        directory.
    :param output: Directory in which to create the index. When omitted, the
        index is created at ``<workspace>/report-index``.
    :return: The index directory and the links created there.
    :raises FileNotFoundError: If the workspace is not initialized or its
        reports directory does not exist.
    :raises FileExistsError: If an index entry would overwrite a real file or
        directory.
    :raises OSError: If a symlink cannot be created or an existing symlink
        cannot be removed.
    """
    workspace_root = Path(workspace).expanduser()
    if not (workspace_root / "workspace.json").is_file():
        raise FileNotFoundError(
            f"Workspace '{workspace_root}' is not initialized; run create-workspace first."
        )

    reports_root = workspace_root / "reports"
    if not reports_root.is_dir():
        raise FileNotFoundError(
            f"Reports directory '{reports_root}' does not exist; run report first."
        )

    index_directory = (
        Path(output).expanduser() if output is not None else workspace_root / "report-index"
    )
    index_directory.mkdir(parents=True, exist_ok=True)

    # The index directory is owned by this command: stale symlinks are safe to
    # remove, while real files and directories are deliberately preserved.
    for entry in index_directory.iterdir():
        if entry.is_symlink():
            entry.unlink()

    report_targets: list[tuple[str, Path]] = []
    for report_path in sorted(reports_root.glob("*/report.txt")):
        if report_path.is_file():
            report_targets.append((report_path.parent.name, report_path))
    for filename in ("summary.md", "similarity-report.txt"):
        report_path = reports_root / filename
        if report_path.is_file():
            report_targets.append((filename, report_path))

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
