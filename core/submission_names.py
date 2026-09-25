"""Read and maintain workspace-level submission display names."""

from __future__ import annotations

import csv
from pathlib import Path


SUBMISSION_NAMES_FILENAME = "submission-identifiers.csv"
SUBMISSION_NAMES_HEADERS = ("submission_identifier", "human_readable_name")


def submission_names_path(workspace: str | Path) -> Path:
    """Return the workspace file containing submission display-name mappings.

    :param workspace: Root directory of the grading workspace.
    :return: Path to the submission identifier mapping CSV file.
    """
    return Path(workspace).expanduser() / SUBMISSION_NAMES_FILENAME


def load_submission_names(workspace: str | Path) -> dict[str, str]:
    """Load non-empty human-readable names from the workspace mapping file.

    :param workspace: Root directory of the grading workspace.
    :return: Mapping from stable submission identifiers to display names.
    :raises ValueError: If the mapping file has an invalid header or duplicate
        submission identifiers.
    """
    path = submission_names_path(workspace)
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if tuple(reader.fieldnames or ()) != SUBMISSION_NAMES_HEADERS:
            raise ValueError(
                f"Submission mapping '{path}' must have columns "
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
                    f"Submission mapping '{path}' contains duplicate identifier "
                    f"'{identifier}'."
                )
            if name:
                mappings[identifier] = name
    return mappings


def sync_submission_names(workspace: str | Path, identifiers: list[str]) -> Path:
    """Add newly imported identifiers to the workspace mapping CSV.

    Existing human-readable names are preserved, while new rows have an empty
    display-name field for the user to fill in.

    :param workspace: Root directory of the grading workspace.
    :param identifiers: Stable submission identifiers to ensure are present.
    :return: Path to the updated mapping CSV file.
    :raises ValueError: If the existing mapping file is malformed.
    :raises OSError: If the mapping file cannot be written.
    """
    path = submission_names_path(workspace)
    rows: dict[str, str] = {}
    if path.is_file():
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
