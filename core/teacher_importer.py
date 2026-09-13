"""Import teacher-only grading materials into a grading workspace."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import shutil
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True)
class TeacherImportResult:
    """Describe the artifacts imported from one teacher archive."""

    raw_archive: Path
    template_member: str
    template_files: tuple[str, ...]
    reference_files: tuple[str, ...]
    template_root: Path
    reference_root: Path
    metadata_path: Path
    ignored_template_files: tuple[str, ...] = ()


class TeacherImporter:
    """Import a teacher ZIP and its nested student-template ZIP.

    :param archive_path: Outer teacher ZIP to import.
    :param output_root: Initialized grading workspace receiving the artifacts.
    :param template_member: Exact member name of the nested template ZIP.
    """

    def __init__(
        self,
        archive_path: str | Path,
        output_root: str | Path,
        template_member: str,
    ) -> None:
        self.archive_path = Path(archive_path).expanduser()
        self.output_root = Path(output_root).expanduser()
        self.template_member = template_member

    def import_teacher_archive(self) -> TeacherImportResult:
        """Copy and unpack teacher materials into the workspace.

        :return: Paths and names of the imported teacher artifacts.
        :raises FileNotFoundError: If the teacher archive or workspace is absent.
        :raises ValueError: If an archive is malformed, unsafe, or does not
            contain the selected template ZIP.
        """
        if not self.archive_path.is_file():
            raise FileNotFoundError(f"Teacher ZIP '{self.archive_path}' was not found.")
        if not (self.output_root / "workspace.json").is_file():
            raise FileNotFoundError(
                f"Workspace '{self.output_root}' is not initialized; run create-workspace first."
            )

        raw_archive = self.output_root / "raw" / self.archive_path.name
        raw_archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.archive_path, raw_archive)
        references_root = self.output_root / "references"
        teacher_root = references_root / "teacher"
        template_root = references_root / "template"
        teacher_root.mkdir(parents=True, exist_ok=True)
        template_root.mkdir(parents=True, exist_ok=True)

        try:
            with ZipFile(self.archive_path) as archive:
                entries = self._safe_entries(archive)
                if self.template_member not in entries:
                    raise ValueError(
                        f"Template ZIP '{self.template_member}' was not found in teacher archive."
                    )
                if not self.template_member.lower().endswith(".zip"):
                    raise ValueError("The selected teacher template must be a ZIP file.")

                reference_files: list[str] = []
                for member in entries:
                    if member == self.template_member:
                        continue
                    target = teacher_root / Path(PurePosixPath(member))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, target.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
                    reference_files.append(member)

                import io

                with archive.open(self.template_member) as source:
                    template_data = io.BytesIO(source.read())
                try:
                    with ZipFile(template_data) as template_archive:
                        template_files = self._extract_template(
                            template_archive, template_root
                        )
                        ignored_template_files = [
                            info.filename for info in template_archive.infolist()
                            if not info.is_dir()
                            and PurePosixPath(info.filename).name.endswith(
                                ".grader-ignore"
                            )
                        ]
                except BadZipFile as error:
                    raise ValueError("The selected teacher template is not a valid ZIP file.") from error
        except BadZipFile as error:
            raise ValueError(f"Teacher ZIP '{self.archive_path}' is not a valid ZIP file.") from error
        metadata = {
            "source_archive": str(self.archive_path),
            "template_member": self.template_member,
            "template_files": template_files,
            "ignored_template_files": ignored_template_files,
            "reference_files": reference_files,
        }
        with (references_root / "teacher_metadata.json").open("w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2)
            file.write("\n")
        return TeacherImportResult(
            raw_archive,
            self.template_member,
            tuple(template_files),
            tuple(reference_files),
            template_root,
            teacher_root,
            references_root / "teacher_metadata.json",
            tuple(ignored_template_files),
        )

    def find_template_members(self) -> list[str]:
        """Find candidate nested ZIP files in the teacher archive.

        :return: Safe, non-directory archive members whose names end in
            ``.zip``.
        :raises FileNotFoundError: If the teacher archive does not exist.
        :raises ValueError: If the archive is malformed or contains an unsafe
            path.
        """
        if not self.archive_path.is_file():
            raise FileNotFoundError(f"Teacher ZIP '{self.archive_path}' was not found.")
        try:
            with ZipFile(self.archive_path) as archive:
                return [
                    member
                    for member in self._safe_entries(archive)
                    if member.lower().endswith(".zip")
                ]
        except BadZipFile as error:
            raise ValueError(f"Teacher ZIP '{self.archive_path}' is not a valid ZIP file.") from error

    @staticmethod
    def _safe_entries(archive: ZipFile) -> list[str]:
        """Return non-directory members that remain inside the archive root.

        :param archive: Outer teacher archive being inspected.
        :return: Safe member names in archive order.
        :raises ValueError: If a member uses an absolute or parent-traversing path.
        """
        entries: list[str] = []
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if info.is_dir():
                continue
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe path in teacher archive: '{info.filename}'.")
            entries.append(info.filename)
        return entries

    @staticmethod
    def _extract_template(archive: ZipFile, destination: Path) -> list[str]:
        """Extract template files while excluding grader-ignore markers.

        :param archive: Nested student-template archive.
        :param destination: Directory receiving the extracted template.
        :return: Relative names of copied template files.
        :raises ValueError: If a nested member path is unsafe.
        """
        copied: list[str] = []
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if info.is_dir():
                continue
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe path in teacher template: '{info.filename}'.")
            if path.name.endswith(".grader-ignore"):
                continue
            target = destination / Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            copied.append(info.filename)
        return copied


def import_teacher_archive(
    archive_path: str | Path,
    output_root: str | Path,
    template_member: str,
) -> TeacherImportResult:
    """Import a teacher archive with a convenience function.

    :param archive_path: Outer teacher ZIP to import.
    :param output_root: Initialized grading workspace receiving the artifacts.
    :param template_member: Exact member name of the nested template ZIP.
    :return: Description of imported teacher artifacts.
    """
    return TeacherImporter(archive_path, output_root, template_member).import_teacher_archive()
