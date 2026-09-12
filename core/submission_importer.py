"""Import and normalize student-canvas-submissions."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path, PurePosixPath
import re
import shutil
from typing import Iterable, Mapping
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True)
class Submission:
    """Describe one normalized submission and its source provenance."""

    identifier: str
    original_filename: str
    source_path: str
    workspace: Path
    files: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    recovered_from_archive: bool = False


@dataclass
class ImportResult:
    """Contain all imported submissions and archive-level warnings."""

    submissions: list[Submission] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_archive: Path | None = None


class SubmissionImporter:
    """Convert a Canvas bulk ZIP into isolated, normalized workspaces.

    :param archive_path: Student-canvas-submissions ZIP to import.
    :param output_root: Directory receiving the raw archive and workspaces.
    :param required_filename: Student file expected by the milestone.
    :param optional_filenames: Files that may accompany the required file.
    """

    def __init__(
        self,
        archive_path: str | Path,
        output_root: str | Path,
        required_filename: str | None = None,
        optional_filenames: Iterable[str] = ("README.md",),
    ) -> None:
        self.archive_path = Path(archive_path)
        self.output_root = Path(output_root)
        self.required_filename = required_filename
        self.optional_filenames = frozenset(optional_filenames)

    def import_submissions(self) -> ImportResult:
        """Import every discoverable submission from the configured ZIP.

        :return: Imported submissions plus warnings that require TA review.
        :raises FileNotFoundError: If the input ZIP does not exist.
        :raises ValueError: If the input is not a valid ZIP archive.
        """
        if not self.archive_path.is_file():
            raise FileNotFoundError(f"Student-canvas-submissions '{self.archive_path}' was not found.")
        self.output_root.mkdir(parents=True, exist_ok=True)
        raw_archive = self.output_root / "raw" / self.archive_path.name
        raw_archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.archive_path, raw_archive)

        try:
            with ZipFile(self.archive_path) as archive:
                entries = self._safe_entries(archive)
                groups = self._discover_groups(entries)
                result = ImportResult(raw_archive=raw_archive)
                names: dict[str, int] = {}
                for source_name, members in groups:
                    submission = self._import_group(
                        archive, source_name, members, names
                    )
                    result.submissions.append(submission)
                    result.warnings.extend(
                        f"{submission.original_filename}: {warning}"
                        for warning in submission.warnings
                    )
                if not result.submissions:
                    result.warnings.append("The student-canvas-submissions contains no files.")
                return result
        except BadZipFile as error:
            raise ValueError(f"Student-canvas-submissions '{self.archive_path}' is not a valid ZIP file.") from error

    def _safe_entries(self, archive: ZipFile) -> list[str]:
        """Return non-directory archive entries and reject unsafe paths.

        :param archive: Open ZIP archive being inspected.
        :return: Valid POSIX member names.
        :raises ValueError: If a member escapes the archive root.
        """
        entries: list[str] = []
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if info.is_dir():
                continue
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe path in student-canvas-submissions: '{info.filename}'.")
            entries.append(info.filename)
        return entries

    def _discover_groups(self, entries: list[str]) -> list[tuple[str, list[str]]]:
        """Group archive files into direct or nested submissions.

        :param entries: Safe file names from the bulk archive.
        :return: Pairs of display source name and member names.
        """
        original_paths = [PurePosixPath(name) for name in entries]
        paths = original_paths
        wrapper = bool(paths and all(path.parts[0].lower() == "submissions" for path in paths))
        if wrapper:
            paths = [PurePosixPath(*path.parts[1:]) for path in paths]
        nested = any(len(path.parts) > 1 for path in paths)
        if not nested:
            return [(path.name, [str(original_paths[index])]) for index, path in enumerate(paths)]
        groups: dict[str, list[str]] = {}
        for index, path in enumerate(paths):
            group = path.parts[0]
            groups.setdefault(group, []).append(str(original_paths[index]))
        return [(name, members) for name, members in groups.items()]

    def _import_group(
        self,
        archive: ZipFile,
        source_name: str,
        members: list[str],
        used_names: dict[str, int],
    ) -> Submission:
        """Normalize one discovered submission and write its metadata.

        :param archive: Open bulk ZIP containing the submission.
        :param source_name: Original Canvas filename or nested submission name.
        :param members: Archive members belonging to this submission.
        :param used_names: Previously allocated internal names.
        :return: The normalized submission record.
        """
        preferred_name = self._internal_name(source_name)
        identifier = self._unique_name(preferred_name, used_names)
        workspace = self.output_root / "submissions" / identifier
        workspace.mkdir(parents=True, exist_ok=False)
        warnings: list[str] = []
        if identifier != preferred_name:
            warnings.append(
                f"internal name '{preferred_name}' collided; assigned '{identifier}'"
            )
        copied: list[str] = []
        recovered = False

        if len(members) == 1 and members[0].lower().endswith(".zip"):
            recovered, copied, archive_warnings = self._recover_zip(
                archive, members[0], workspace
            )
            warnings.extend(archive_warnings)
        else:
            for member in members:
                member_name = PurePosixPath(member).name
                target = workspace / self._normalized_filename(member_name)
                with archive.open(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                copied.append(target.name)
            if len(members) > 1:
                warnings.append("multiple files were submitted; extra files are ignored by normalization")

        metadata = {
            "identifier": identifier,
            "original_filename": source_name,
            "source_archive": str(self.archive_path),
            "source_members": members,
            "recovered_from_archive": recovered,
            "files": copied,
            "warnings": warnings,
        }
        with (workspace / "submission_metadata.json").open("w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2)
        return Submission(identifier, source_name, str(self.archive_path), workspace,
                          tuple(copied), tuple(warnings), recovered)

    def _normalized_filename(self, filename: str) -> str:
        """Choose the normalized filename used by downstream grading.

        :param filename: Basename supplied by the Canvas export.
        :return: Configured milestone filename when the export contains it as
            a suffix; otherwise the original basename.
        """
        if self.required_filename:
            expected = Path(self.required_filename).name
            if filename.lower() == expected.lower() or filename.lower().endswith(
                ("_" + expected).lower()
            ):
                return expected
        return filename

    def _recover_zip(self, archive: ZipFile, member: str, workspace: Path) -> tuple[bool, list[str], list[str]]:
        """Recover root-level milestone files from a submitted ZIP.

        :param archive: Open bulk ZIP containing the submitted ZIP.
        :param member: Member name of the submitted ZIP.
        :param workspace: Destination normalized workspace.
        :return: Recovery flag, copied names, and review warnings.
        """
        copied: list[str] = []
        warnings = ["submission ZIP preserved in the raw archive and root files were recovered"]
        if self.required_filename is None:
            return False, copied, ["submitted ZIP cannot be normalized without a required filename"]
        import io
        with archive.open(member) as source:
            data = io.BytesIO(source.read())
        try:
            with ZipFile(data) as submitted:
                root = [info for info in submitted.infolist()
                        if not info.is_dir() and len(PurePosixPath(info.filename).parts) == 1]
                required = [info for info in root if info.filename == self.required_filename]
                if len(required) != 1:
                    return False, copied, ["required file is missing or ambiguous at the submitted ZIP root"]
                allowed = {self.required_filename, *self.optional_filenames}
                for info in root:
                    if info.filename in allowed:
                        target = workspace / info.filename
                        with submitted.open(info) as source, target.open("wb") as destination:
                            shutil.copyfileobj(source, destination)
                        copied.append(info.filename)
                    elif info.filename != self.required_filename:
                        warnings.append(f"extra file '{info.filename}' was ignored")
                if any(len(PurePosixPath(info.filename).parts) > 1 for info in submitted.infolist()):
                    warnings.append("nested files in the submitted ZIP require manual review")
                return True, copied, warnings
        except BadZipFile:
            return False, copied, ["submitted ZIP is malformed"]

    def _internal_name(self, source_name: str) -> str:
        """Create a stable filesystem-safe name from a Canvas filename.

        :param source_name: Original source filename or nested submission name.
        :return: Sanitized internal submission name.
        """
        stem = Path(source_name).stem
        stem = re.sub(r"\s*\[LATE\]\s*", "_", stem, flags=re.IGNORECASE)
        stem = re.sub(r"[-_]\d+$", "", stem)
        if self.required_filename:
            required_stem = Path(self.required_filename).stem
            stem = re.sub(rf"(?:[-_ ]+){re.escape(required_stem)}$", "", stem, flags=re.IGNORECASE)
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
        return stem or "submission"

    @staticmethod
    def _unique_name(name: str, used_names: dict[str, int]) -> str:
        """Disambiguate an internal name without discarding a submission.

        :param name: Preferred internal name.
        :param used_names: Mutable map of allocated names and occurrence counts.
        :return: Unique deterministic name.
        """
        count = used_names.get(name, 0)
        used_names[name] = count + 1
        return name if count == 0 else f"{name}-{count + 1}"


def import_submissions(
    archive_path: str | Path,
    output_root: str | Path,
    required_filename: str | None = None,
    optional_filenames: Iterable[str] = ("README.md",),
) -> ImportResult:
    """Import student-canvas-submissions using a one-call convenience interface.

    :param archive_path: Student-canvas-submissions ZIP to import.
    :param output_root: Directory receiving the imported workspaces.
    :param required_filename: Student file expected by the milestone.
    :param optional_filenames: Files allowed alongside the required file.
    :return: Imported submissions and warnings.
    """
    return SubmissionImporter(
        archive_path,
        output_root,
        required_filename,
        optional_filenames,
    ).import_submissions()
