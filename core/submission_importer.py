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
        required_filenames: Iterable[str] | None = None,
        structured_submissions: bool = False,
    ) -> None:
        self.archive_path = Path(archive_path)
        self.output_root = Path(output_root)
        self.required_filename = required_filename
        self.optional_filenames = frozenset(optional_filenames)
        self.required_filenames = tuple(
            required_filenames or ((required_filename,) if required_filename else ())
        )
        self.structured_submissions = structured_submissions

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
        workspace = self.output_root / "students" / identifier
        workspace.mkdir(parents=True, exist_ok=False)
        if self.structured_submissions:
            return self._import_structured_group(
                archive, source_name, members, used_names, identifier, workspace
            )
        source_root = workspace / "src-files"
        source_root.mkdir()
        warnings: list[str] = []
        if identifier != preferred_name:
            warnings.append(
                f"internal name '{preferred_name}' collided; assigned '{identifier}'"
            )
        copied: list[str] = []
        recovered = False

        if len(members) == 1 and members[0].lower().endswith(".zip"):
            recovered, copied, archive_warnings = self._recover_zip(
                archive, members[0], source_root
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
                target = source_root / normalized_name
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

    def _import_structured_group(
        self,
        archive: ZipFile,
        source_name: str,
        members: list[str],
        used_names: dict[str, int],
        identifier: str,
        workspace: Path,
    ) -> Submission:
        """Import a Milestone 2 ZIP with source files and UML artifacts.

        :param archive: Open outer Canvas archive.
        :param source_name: Canvas-generated name for the submission group.
        :param members: Outer-archive members belonging to the student.
        :param used_names: Allocated submission identifiers.
        :param identifier: Normalized identifier assigned to this submission.
        :param workspace: Destination student workspace.
        :return: Imported submission record with layout warnings.
        """
        source_root = workspace / "src-files"
        uml_root = workspace / "uml-diagrams"
        source_root.mkdir()
        uml_root.mkdir()
        warnings: list[str] = []
        copied: list[str] = []
        uml_metadata: dict[str, object] = {
            "status": "missing_directory",
            "directory": None,
            "class_files": [],
            "sequence_files": [],
            "files": [],
        }

        zip_members = [member for member in members if member.lower().endswith(".zip")]
        if len(zip_members) != 1:
            warnings.append("expected exactly one submitted ZIP file")
            if not zip_members:
                warnings.append("submission is not a ZIP and could not be structurally imported")
            else:
                warnings.append(f"multiple submitted ZIP files found: {zip_members}")
            metadata = self._write_structured_metadata(
                workspace, identifier, source_name, members, copied, warnings,
                uml_metadata, self.required_filenames,
            )
            return Submission(identifier, source_name, str(self.archive_path), workspace,
                              tuple(copied), tuple(warnings), False)

        import io
        with archive.open(zip_members[0]) as source:
            data = io.BytesIO(source.read())
        try:
            with ZipFile(data) as submitted:
                entries = self._safe_entries(submitted)
                duplicate_paths = [
                    name for name in dict.fromkeys(entries) if entries.count(name) > 1
                ]
                if duplicate_paths:
                    warnings.append(f"duplicate ZIP entries found: {duplicate_paths}")
                top_dirs = []
                root_files = []
                for name in entries:
                    path = PurePosixPath(name)
                    if len(path.parts) == 1:
                        root_files.append(name)
                    elif path.parts[0] not in top_dirs:
                        top_dirs.append(path.parts[0])
                if len(top_dirs) != 1:
                    warnings.append(
                        f"expected one top-level directory; found {top_dirs or 'none'}"
                    )
                    metadata = self._write_structured_metadata(
                        workspace, identifier, source_name, members, copied,
                        warnings, uml_metadata, self.required_filenames,
                    )
                    return Submission(identifier, source_name, str(self.archive_path), workspace,
                                      tuple(copied), tuple(warnings), False)
                project_dir = top_dirs[0]
                if root_files:
                    warnings.append(f"files outside the top-level directory: {root_files}")
                direct_files = [
                    name for name in entries
                    if PurePosixPath(name).parts[:1] == (project_dir,)
                    and len(PurePosixPath(name).parts) == 2
                ]
                allowed = {
                    Path(name).name for name in (*self.required_filenames, *self.optional_filenames)
                }
                for name in direct_files:
                    filename = PurePosixPath(name).name
                    if filename not in allowed:
                        warnings.append(f"additional root file '{filename}' was ignored")
                        continue
                    target = source_root / filename
                    if target.exists():
                        warnings.append(f"duplicate submitted file '{filename}' was ignored")
                        continue
                    with submitted.open(name) as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
                    copied.append(filename)
                for required in self.required_filenames:
                    if Path(required).name not in copied:
                        warnings.append(f"required file '{required}' was not found")

                uml_dirs = [
                    f"{project_dir}/{directory_name}"
                    for directory_name in dict.fromkeys(
                        PurePosixPath(name).parts[1]
                        for name in entries
                        if len(PurePosixPath(name).parts) >= 3
                        and PurePosixPath(name).parts[0] == project_dir
                    )
                    if "uml" in directory_name.lower()
                ]
                selected_uml = uml_dirs[0] if uml_dirs else None
                if len(uml_dirs) > 1:
                    warnings.append(f"additional UML directories ignored: {uml_dirs[1:]}")
                parent_matches = [
                    name for name in direct_files
                    if "uml" in PurePosixPath(name).name.lower()
                    and ("class" in PurePosixPath(name).name.lower()
                         or "sequence" in PurePosixPath(name).name.lower())
                ]
                if selected_uml:
                    uml_metadata["directory"] = selected_uml
                    uml_files = [
                        name for name in entries
                        if len(PurePosixPath(name).parts) == 3
                        and PurePosixPath(name).parts[:2] == PurePosixPath(selected_uml).parts
                    ]
                    self._copy_uml_files(
                        submitted, uml_files, uml_root, uml_metadata, warnings
                    )
                    if parent_matches:
                        warnings.append(
                            f"UML files outside the selected UML directory were ignored: {parent_matches}"
                        )
                else:
                    fallback = parent_matches
                    if fallback:
                        warnings.append("UML files were found in the project root instead of an UML directory")
                        uml_metadata["status"] = "fallback_files_outside_uml_directory"
                        self._copy_uml_files(
                            submitted, fallback, uml_root, uml_metadata, warnings
                        )
                    else:
                        warnings.append("no UML directory or qualifying UML files were found")
                if selected_uml and uml_metadata["status"] == "missing_directory":
                    uml_metadata["status"] = "complete"
                    class_files = uml_metadata["class_files"]
                    sequence_files = uml_metadata["sequence_files"]
                    if not class_files:
                        uml_metadata["status"] = "missing_class"
                    if not sequence_files:
                        uml_metadata["status"] = "missing_sequence" if class_files else "missing_class_and_sequence"
        except BadZipFile:
            warnings.append("submitted ZIP is malformed")
        self._write_structured_metadata(
            workspace, identifier, source_name, members, copied, warnings, uml_metadata
            , self.required_filenames
        )
        return Submission(identifier, source_name, str(self.archive_path), workspace,
                          tuple(copied), tuple(warnings), False)

    def _copy_uml_files(
        self,
        submitted: ZipFile,
        members: list[str],
        destination: Path,
        uml_metadata: dict[str, object],
        warnings: list[str],
    ) -> None:
        """Copy matching direct UML files and record their classifications.

        :param submitted: Open student submission ZIP.
        :param members: Direct UML file members to inspect.
        :param destination: Student ``uml-diagrams`` directory.
        :param uml_metadata: Mutable UML metadata record.
        :param warnings: Mutable warning collection.
        """
        class_files = uml_metadata["class_files"]
        sequence_files = uml_metadata["sequence_files"]
        copied_files = uml_metadata["files"]
        assert isinstance(class_files, list)
        assert isinstance(sequence_files, list)
        assert isinstance(copied_files, list)
        for member in members:
            filename = PurePosixPath(member).name
            lowered = filename.lower()
            is_class = "class" in lowered
            is_sequence = "sequence" in lowered
            if not is_class and not is_sequence:
                warnings.append(f"additional UML-directory file '{filename}' was ignored")
                continue
            target = destination / filename
            if target.exists():
                warnings.append(f"duplicate UML filename '{filename}' was ignored")
                continue
            with submitted.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            copied_files.append(filename)
            if is_class:
                class_files.append(filename)
            if is_sequence:
                sequence_files.append(filename)
            if is_class and is_sequence:
                warnings.append(f"UML file '{filename}' matched both class and sequence")
        if any(name in class_files for name in sequence_files):
            uml_metadata["status"] = "one_file_matches_both"

    @staticmethod
    def _write_structured_metadata(
        workspace: Path,
        identifier: str,
        source_name: str,
        members: list[str],
        copied: list[str],
        warnings: list[str],
        uml_metadata: dict[str, object],
        required_files: Iterable[str],
    ) -> dict[str, object]:
        """Write metadata for a structured submission import.

        :param workspace: Destination student workspace.
        :param identifier: Normalized submission identifier.
        :param source_name: Canvas-generated source name.
        :param members: Outer-archive members for the submission.
        :param copied: Copied source filenames.
        :param warnings: Import warnings requiring review.
        :param uml_metadata: UML discovery and classification metadata.
        :return: Metadata written to disk.
        """
        metadata = {
            "identifier": identifier,
            "original_filename": source_name,
            "source_members": members,
            "files": copied,
            "student_files": copied,
            "required_files": [],
            "warnings": warnings,
            "uml": uml_metadata,
        }
        metadata["required_files"] = [Path(name).name for name in required_files]
        (workspace / "submission_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        return metadata

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
        :param workspace: Destination ``src-files`` directory.
        :return: Recovery flag, copied names, and review warnings.
        """
        copied: list[str] = []
        zip_warning = (
            "student submitted a ZIP file; checking the root of the student's "
            "ZIP submission for required files"
        )
        warnings = [
            zip_warning,
            "submission ZIP preserved in the raw archive and root files were recovered",
        ]
        if self.required_filename is None:
            return False, copied, [
                zip_warning,
                "submitted ZIP cannot be normalized without a required filename",
            ]
        import io
        with archive.open(member) as source:
            data = io.BytesIO(source.read())
        try:
            with ZipFile(data) as submitted:
                root = [info for info in submitted.infolist()
                        if not info.is_dir() and len(PurePosixPath(info.filename).parts) == 1]
                required = [info for info in root if info.filename == self.required_filename]
                if len(required) != 1:
                    return False, copied, [
                        zip_warning,
                        "required file is missing or ambiguous at the root of "
                        "the student's ZIP submission",
                    ]
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
            return False, copied, [zip_warning, "submitted ZIP is malformed"]

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
