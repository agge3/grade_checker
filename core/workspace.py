"""Create the on-disk structure used by a grading run."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


WORKSPACE_DIRECTORIES = (
    "raw",
    "students",
    "build-workspaces",
    "runs",
    "references",
)


@dataclass(frozen=True)
class Workspace:
    """Describe an initialized grading workspace."""

    root: Path
    milestone: str | None
    configuration_path: Path


def create_workspace(
    root: str | Path,
    milestone: str | None = None,
    configuration_path: str | Path | None = None,
) -> Workspace:
    """Create an empty grading workspace and record its settings.

    :param root: Directory to create for the grading workspace.
    :param milestone: Optional milestone configuration name associated with the
        workspace.
    :param configuration_path: Optional path to the milestone configuration
        file. It is stored as metadata and is not copied or modified.
    :return: Description of the initialized workspace.
    :raises FileExistsError: If the workspace already has a configuration file.
    :raises OSError: If the directory structure cannot be created.
    """
    workspace_root = Path(root).expanduser()
    configuration_file = workspace_root / "workspace.json"
    if configuration_file.exists():
        raise FileExistsError(
            f"Workspace configuration '{configuration_file}' already exists."
        )

    workspace_root.mkdir(parents=True, exist_ok=True)
    for directory in WORKSPACE_DIRECTORIES:
        (workspace_root / directory).mkdir(exist_ok=True)

    metadata = {
        "workspace_version": 2,
        "milestone": milestone,
        "milestone_configuration": str(configuration_path)
        if configuration_path is not None
        else None,
        "directories": {directory: directory for directory in WORKSPACE_DIRECTORIES},
    }
    with configuration_file.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)
        file.write("\n")
    return Workspace(workspace_root, milestone, configuration_file)
