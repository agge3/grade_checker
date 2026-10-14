"""Read and maintain workspace-level submission display names."""

from __future__ import annotations

import csv
import json
from pathlib import Path


SUBMISSION_NAMES_FILENAME = "submission-identifiers.csv"
SUBMISSION_NAMES_HEADERS = ("submission_identifier", "human_readable_name")


def submission_names_path(workspace: str | Path) -> Path:
    """Return the workspace file containing submission display-name mappings.

    :param workspace: Root directory of the grading workspace.
    :return: Path to the submission identifier mapping CSV file.
    """
    return Path(workspace).expanduser() / SUBMISSION_NAMES_FILENAME


def configured_submission_names_path(workspace: str | Path) -> Path | None:
    """Return the externally configured identifier mapping for a workspace.

    :param workspace: Root directory of the grading workspace.
    :return: Recorded external mapping path, or ``None`` when the workspace
        does not specify one.
    :raises ValueError: If workspace metadata is malformed.
    """
    workspace_root = Path(workspace).expanduser()
    configuration_path = workspace_root / "workspace.json"
    if not configuration_path.is_file():
        return None
    metadata = json.loads(configuration_path.read_text(encoding="utf-8"))
    identifier_file = metadata.get("identifier_file")
    if identifier_file is None:
        return None
    if not isinstance(identifier_file, str) or not identifier_file:
        raise ValueError(
            f"Workspace configuration '{configuration_path}' has an invalid "
            "identifier_file value."
        )
    return Path(identifier_file).expanduser()


def load_submission_names(workspace: str | Path) -> dict[str, str]:
    """Load non-empty human-readable names from the workspace mapping file.

    :param workspace: Root directory of the grading workspace.
    :return: Mapping from stable submission identifiers to display names.
    :raises ValueError: If the mapping file has an invalid header or duplicate
        submission identifiers.
    """
    configured_path = configured_submission_names_path(workspace)
    path = configured_path or submission_names_path(workspace)
    if not path.is_file():
        if configured_path is not None:
            raise FileNotFoundError(
                f"Configured student identifier file '{path}' was not found."
            )
        return {}
    return load_submission_names_file(path)


def load_submission_names_file(path: str | Path) -> dict[str, str]:
    """Load non-empty human-readable names from a mapping CSV file.

    :param path: CSV file containing the standard identifier mapping headers.
    :return: Mapping from stable submission identifiers to display names.
    :raises FileNotFoundError: If the mapping file does not exist.
    :raises ValueError: If the mapping file has an invalid header or duplicate
        submission identifiers.
    """
    mapping_path = Path(path).expanduser()
    if not mapping_path.is_file():
        raise FileNotFoundError(f"Student identifier file '{mapping_path}' was not found.")
    with mapping_path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != SUBMISSION_NAMES_HEADERS:
            raise ValueError(
                f"Submission mapping '{mapping_path}' must have columns "
                f"{','.join(SUBMISSION_NAMES_HEADERS)}."
            )
        mappings: dict[str, str] = {}
        for row in reader:
            identifier = (row.get(SUBMISSION_NAMES_HEADERS[0]) or "").strip()
            name = (row.get(SUBMISSION_NAMES_HEADERS[1]) or "").strip()
            if not identifier:
                continue
            if identifier in mappings:
                raise ValueError(
                    f"Submission mapping '{mapping_path}' contains duplicate identifier "
                    f"'{identifier}'."
                )
            if name:
                mappings[identifier] = name
    return mappings


def sync_submission_names(workspace: str | Path, identifiers: list[str]) -> Path:
    """Validate or update the mapping used by a workspace.

    External mappings are validated in place and never modified. Legacy local
    mappings are updated when they already exist; a missing local mapping is
    left absent.

    :param workspace: Root directory of the grading workspace.
    :param identifiers: Stable submission identifiers to ensure are present.
    :return: Path to the updated mapping CSV file.
    :raises ValueError: If the existing mapping file is malformed.
    :raises OSError: If the mapping file cannot be written.
    """
    configured_path = configured_submission_names_path(workspace)
    if configured_path is not None:
        if not configured_path.is_file():
            raise FileNotFoundError(
                f"Configured student identifier file '{configured_path}' was not found."
            )
        load_submission_names_file(configured_path)
        return configured_path

    path = submission_names_path(workspace)
    if not path.is_file():
        return path
    rows: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != SUBMISSION_NAMES_HEADERS:
            raise ValueError(f"Submission mapping '{path}' has an invalid header.")
        for row in reader:
            identifier = (row.get(SUBMISSION_NAMES_HEADERS[0]) or "").strip()
            if identifier in rows:
                raise ValueError(
                    f"Submission mapping '{path}' contains duplicate identifier "
                    f"'{identifier}'."
                )
            if identifier:
                rows[identifier] = (
                    row.get(SUBMISSION_NAMES_HEADERS[1]) or ""
                ).strip()
    for identifier in identifiers:
        rows.setdefault(identifier, "")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(SUBMISSION_NAMES_HEADERS)
        writer.writerows(
            (identifier, rows[identifier])
            for identifier in sorted(rows, key=str.casefold)
        )
    return path


def display_submission_name(identifier: str, names: dict[str, str]) -> str:
    """Return a mapped display name or the stable identifier as a fallback.

    :param identifier: Stable normalized submission identifier.
    :param names: Workspace mapping loaded by :func:`load_submission_names`.
    :return: Human-readable name when configured, otherwise ``identifier``.
    """
    return names.get(identifier, identifier)


def format_submission_label(identifier: str, names: dict[str, str]) -> str:
    """Format a user-facing label while retaining the stable key when mapped.

    :param identifier: Stable normalized submission identifier.
    :param names: Workspace mapping loaded by :func:`load_submission_names`.
    :return: Identifier alone when unmapped, or readable name plus identifier.
    """
    display_name = display_submission_name(identifier, names)
    return display_name if display_name == identifier else f"{display_name} [{identifier}]"
