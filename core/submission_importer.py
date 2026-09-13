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
        if self.archive_path.resolve() != raw_archive.resolve():
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
        groups: dict[str, tuple[str, list[str]]] = {}
        for index, path in enumerate(paths):
            if len(path.parts) > 1:
                group = self._directory_group_key(path.parts[0])
                # Use the normalized directory key for naming; original
                # members remain available in metadata for audit purposes.
                display_name = group
            elif self.required_filename:
                group = self._submission_group_key(path.name)
                display_name = group
            else:
                group = path.name
                display_name = path.name
            if group not in groups:
                groups[group] = (display_name, [])
            groups[group][1].append(str(original_paths[index]))
        return list(groups.values())

    @staticmethod
    def _directory_group_key(directory_name: str) -> str:
        """Normalize a directory name used to contain one submission.

        :param directory_name: First directory component from an archive path.
        :return: Grouping key with a per-file numeric suffix removed when one
            is present.
        """
        return re.sub(r"^(.+[-_]\d+)[-_]\d+(?:[-_].*)?$", r"\1", directory_name)

    def _submission_group_key(self, filename: str) -> str:
        """Find the shared Canvas metadata prefix for a direct file.

        :param filename: Basename generated by the Canvas export.
        :return: Key shared by files belonging to the same submission.
        """
        stem = Path(filename).stem
        # Canvas filenames use the shared student/first-number prefix, then
        # may add a per-file number and any uploaded filename. The uploaded
        # filename is intentionally not used for grouping because it may be a
        # source file, a ZIP, or another file type.
        match = re.match(r"^(.+?[-_]\d+)(?:[-_]\d+)?(?:[-_].+)$", stem)
        return match.group(1) if match else stem

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
                normalized_name = self._normalized_filename(member_name)
                allowed_names = {
                    Path(self.required_filename).name
                    if self.required_filename else "",
                    *(Path(name).name for name in self.optional_filenames),
                }
                if normalized_name not in allowed_names:
                    warnings.append(f"extra file '{member_name}' was ignored")
                    continue
                target = workspace / normalized_name
                with archive.open(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
                copied.append(target.name)
            if len(members) > 1 and not copied:
                warnings.append("multiple files were submitted but none matched the configured files")

        metadata = {
            "identifier": identifier,
            "original_filename": source_name,
            "source_archive": str(self.archive_path),
            "source_members": members,
            "recovered_from_archive": recovered,
            "files": copied,
            "student_files": copied,
            "required_files": [self.required_filename]
            if self.required_filename
            else [],
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
            expected_names = [self.required_filename, *self.optional_filenames]
            for expected_name in expected_names:
                expected = Path(expected_name).name
                filename_stem = Path(filename).stem
                expected_stem = Path(expected).stem
                suffix_pattern = (
                    rf"(?:^|[-_ ]){re.escape(expected_stem)}(?:-\d+)?$"
                )
                if re.search(suffix_pattern, filename_stem, re.IGNORECASE):
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
        stem = self._submission_group_key(source_name)
        stem = re.sub(r"\s*\[LATE\]\s*", "_", stem, flags=re.IGNORECASE)
        known_names = [self.required_filename, *self.optional_filenames]
        matched_filename = False
        for known_name in known_names:
            if known_name:
                known_stem = Path(known_name).stem
                normalized_stem = re.sub(
                    rf"(?:[-_ ]+){re.escape(known_stem)}$",
                    "",
                    stem,
                    flags=re.IGNORECASE,
                )
                matched_filename = matched_filename or normalized_stem != stem
                stem = normalized_stem
        # The final numeric metadata component identifies the uploaded file,
        # not the submission, so it must not be part of the workspace name.
        if matched_filename:
            stem = re.sub(r"[-_]\d+$", "", stem)
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
