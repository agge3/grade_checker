"""Tests for the command-line orchestration layer."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json

import main
from core.teacher_importer import TeacherImporter


class CreateWorkspaceTests(unittest.TestCase):
    """Verify the public workspace-creation command delegates correctly."""

    @patch("builtins.input", return_value="")
    def test_create_workspace_creates_empty_layout(self, input_mock) -> None:
        """Ensure initialization creates directories and workspace metadata."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "workspace"
            status = main.create_workspace(["--output", str(output)])
            self.assertEqual(status, 0)
            for name in ("raw", "submissions", "build-workspaces", "reports", "references"):
                self.assertTrue((output / name).is_dir())
            metadata = json.loads((output / "workspace.json").read_text(encoding="utf-8"))
            self.assertIsNone(metadata["milestone"])

    @patch("main.create_workspace", return_value=0)
    def test_main_dispatches_create_workspace(self, create_workspace) -> None:
        """Ensure the new command does not enter the legacy parser."""
        self.assertEqual(main.main(["create-workspace"]), 0)
        create_workspace.assert_called_once_with([])


class TeacherImportTests(unittest.TestCase):
    """Verify teacher ZIP contents are imported into workspace references."""

    def test_import_teacher_zip_extracts_template_and_references(self) -> None:
        """Ensure the nested template and other teacher files are preserved."""
        from zipfile import ZipFile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "workspace.json").write_text("{}", encoding="utf-8")
            teacher_zip = root / "teacher.zip"
            template_bytes = root / "template.zip"
            with ZipFile(template_bytes, "w") as template:
                template.writestr("CMakeLists.txt", "project(test)")
                template.writestr("notes.grader-ignore", "ignored")
            with ZipFile(teacher_zip, "w") as teacher:
                teacher.write(template_bytes, "student-template.zip")
                teacher.writestr("solution.cpp", "int main() {}")

            result = TeacherImporter(
                teacher_zip, workspace, "student-template.zip"
            ).import_teacher_archive()
            self.assertEqual(result.template_files, ("CMakeLists.txt",))
            self.assertEqual(result.reference_files, ("solution.cpp",))
            self.assertTrue((workspace / "raw" / "teacher.zip").is_file())
            self.assertTrue((workspace / "references/template/CMakeLists.txt").is_file())
            self.assertTrue((workspace / "references/teacher/solution.cpp").is_file())

    @patch("main.import_teacher_zip", return_value=0)
    def test_main_dispatches_teacher_import(self, import_teacher_zip) -> None:
        """Ensure the teacher import command reaches its command handler."""
        self.assertEqual(main.main(["import-teacher-zip"]), 0)
        import_teacher_zip.assert_called_once_with([])


if __name__ == "__main__":
    unittest.main()
