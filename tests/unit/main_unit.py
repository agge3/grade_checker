"""Tests for the command-line orchestration layer."""

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch
import json

import main
from core.report_index import ReportIndexResult
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
            for name in ("raw", "students", "build-workspaces", "runs", "references"):
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

    @patch("main.report", return_value=0)
    def test_main_dispatches_report_command(self, report) -> None:
        """Ensure the explicit report command bypasses legacy flag parsing."""
        self.assertEqual(main.main(["report", "milestone2-hugh"]), 0)
        report.assert_called_once_with(["milestone2-hugh"])

    @patch("main.analyze", return_value=0)
    def test_main_dispatches_analyze_command(self, analyze) -> None:
        """Ensure the standalone analyzer command bypasses legacy parsing."""
        self.assertEqual(
            main.main(["analyze-similarity", "--workspace", "workspace"]), 0
        )
        analyze.assert_called_once_with(["--workspace", "workspace"])

    @patch("main.report_index", return_value=0)
    def test_main_dispatches_generate_index_report_command(self, report_index) -> None:
        """Ensure the generate-index-report command reaches its handler."""
        self.assertEqual(
            main.main(["generate-index-report", "--workspace", "workspace"]), 0
        )
        report_index.assert_called_once_with(["--workspace", "workspace"])

    @patch("main.create_report_index", return_value=ReportIndexResult(Path("index"), ()))
    @patch("main._select_workspace_interactively", return_value="selected-workspace")
    def test_report_index_selects_workspace_interactively(
        self, select_workspace, create_index
    ) -> None:
        """Ensure the index command prompts when no workspace is supplied."""
        self.assertEqual(main.report_index([]), 0)
        select_workspace.assert_called_once_with()
        create_index.assert_called_once_with("selected-workspace", None)

    @patch("main.runtime_log_index", return_value=0)
    def test_main_dispatches_runtime_log_index_command(self, runtime_log_index) -> None:
        """Ensure the runtime log index command reaches its handler."""
        self.assertEqual(main.main(["generate-index-runtime-log"]), 0)
        runtime_log_index.assert_called_once_with([])

    @patch("main.buildtime_log_index", return_value=0)
    def test_main_dispatches_buildtime_log_index_command(self, buildtime_log_index) -> None:
        """Ensure the buildtime log index command reaches its handler."""
        self.assertEqual(main.main(["generate-index-buildtime"]), 0)
        buildtime_log_index.assert_called_once_with([])

    @patch("main.create_file_index", return_value=ReportIndexResult(Path("index"), ()))
    def test_generate_index_accepts_filepath(self, create_index) -> None:
        """Ensure the general index command passes through a requested path."""
        self.assertEqual(
            main.generate_index(["--workspace", "workspace", "--file", "notes.md"]), 0
        )
        create_index.assert_called_once_with("workspace", "notes.md", None)


class WorkspaceReportTests(unittest.TestCase):
    """Verify reporting prepares isolated teacher-template build workspaces."""

    def test_expected_output_classifies_exact_blank_line_and_content_differences(self) -> None:
        """Classify runtime output against the TA reference by difference type."""
        from core.workspace_reporter import WorkspaceReporter

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            reference_root = workspace / "references/teacher"
            reference_root.mkdir(parents=True)
            (workspace / "workspace.json").write_text("{}", encoding="utf-8")
            (reference_root / "expected-output.txt").write_text(
                "first\nsecond\n", encoding="utf-8"
            )
            reporter = WorkspaceReporter(workspace)

            self.assertTrue(
                reporter._check_expected_output(
                    "first\nsecond\n\n\n[exit status: 0]\n"
                ).startswith("newline diff (")
            )
            self.assertTrue(
                reporter._check_expected_output(
                    "first\nsecond\n\n[exit status: 0]\n"
                ).startswith("exact match (")
            )
            self.assertTrue(
                reporter._check_expected_output(
                    "first\nchanged\n[exit status: 0]\n"
                ).startswith("manual review (1 differing line):")
            )
            (reference_root / "expected-output.txt").write_text(
                "First second\n", encoding="utf-8"
            )
            self.assertTrue(
                reporter._check_expected_output(
                    "first   second\n\n[exit status: 0]\n"
                ).startswith("case diff, whitespace diff (0 differing lines):")
            )

    def test_report_overlays_teacher_template(self) -> None:
        """Ensure reporting creates build inputs without changing student import."""
        from core.submission_importer import SubmissionImporter
        from core.workspace_reporter import WorkspaceReporter
        from zipfile import ZipFile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "workspace.json").write_text("{}", encoding="utf-8")
            template_root = workspace / "references/template"
            template_root.mkdir(parents=True)
            (template_root / "CMakeLists.txt").write_text("template", encoding="utf-8")
            (template_root / "support.hpp").write_text("support", encoding="utf-8")
            submissions_zip = root / "submissions.zip"
            with ZipFile(submissions_zip, "w") as archive:
                archive.writestr("student.cpp", "student",)

            result = SubmissionImporter(
                submissions_zip, workspace, required_filename="student.cpp"
            ).import_submissions()
            self.assertFalse(
                (workspace / "build-workspaces" / result.submissions[0].identifier).exists()
            )
            report_result = WorkspaceReporter(workspace).report()
            build_workspace = workspace / "build-workspaces" / result.submissions[0].identifier
            self.assertEqual((build_workspace / "CMakeLists.txt").read_text(), "template")
            self.assertEqual((build_workspace / "support.hpp").read_text(), "support")
            self.assertEqual((build_workspace / "student.cpp").read_text(), "student")
            self.assertEqual(len(report_result.reports), 1)
            student_root = workspace / "students" / result.submissions[0].identifier
            self.assertTrue((student_root / "src-files" / "student.cpp").is_file())
            self.assertEqual(report_result.summary.name, "summary.md")
            self.assertEqual(report_result.summary.parent, workspace)
            summary_text = report_result.summary.read_text(encoding="utf-8")
            self.assertIn("| Submission | Submission status |", summary_text)
            self.assertIn("Methods found (expected:", summary_text)
            self.assertIn("| student    |", summary_text)
            report_text = report_result.reports[0].read_text(encoding="utf-8")
            self.assertIn(f"Workspace path prefix: {workspace}", report_text)
            self.assertIn("<workspace-path>/students/student/build-output.log", report_text)
            self.assertNotIn(f"Student workspace: {workspace}", report_text)
            for section in (
                "File Headers", "Methods", "Method Headers", "GTest Check",
                "Output Check", "Workflow Flags", "Expected output:",
            ):
                self.assertIn(section, report_text)
            self.assertIn("Summary: 0 found, 0 missing.", report_text)
            self.assertNotIn("Raw Build Output", report_text)
            self.assertNotIn("Runtime Output", report_text)
            notes = workspace / "students" / result.submissions[0].identifier / "notes.md"
            notes_text = notes.read_text(encoding="utf-8")
            self.assertIn("different from `report.txt`", notes_text)


class ReportIndexTests(unittest.TestCase):
    """Verify report indexes expose generated reports without copying them."""

    def test_report_index_creates_relative_links_and_refreshes_stale_links(self) -> None:
        """Ensure report links point into the workspace and stale links disappear."""
        from core.report_index import create_report_index

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            students = workspace / "students"
            students.mkdir(parents=True)
            (workspace / "workspace.json").write_text("{}", encoding="utf-8")
            student_report = students / "student01" / "report.txt"
            student_report.parent.mkdir()
            student_report.write_text("grade", encoding="utf-8")
            (workspace / "summary.md").write_text("summary", encoding="utf-8")
            (workspace / "similarity-report.txt").write_text("similarity", encoding="utf-8")
            index = create_report_index(workspace).directory

            self.assertEqual(
                (index / "student01").read_text(encoding="utf-8"), "grade"
            )
            self.assertEqual(os.readlink(index / "student01"), "../students/student01/report.txt")
            self.assertTrue((index / "summary.md").is_symlink())

            student_report.unlink()
            create_report_index(workspace)
            self.assertFalse((index / "student01").exists())

    def test_report_index_does_not_overwrite_real_entries(self) -> None:
        """Ensure an existing real index entry causes a clear failure."""
        from core.report_index import create_report_index

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            report = workspace / "students" / "student01" / "report.txt"
            report.parent.mkdir(parents=True)
            (workspace / "workspace.json").write_text("{}", encoding="utf-8")
            report.write_text("grade", encoding="utf-8")
            index = workspace / "report-index"
            index.mkdir()
            (index / "student01").write_text("keep", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                create_report_index(workspace)

    def test_log_indexes_link_each_existing_submission_log(self) -> None:
        """Ensure runtime and buildtime indexes expose their matching logs."""
        from core.report_index import create_buildtime_log_index, create_runtime_log_index

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            students = workspace / "students"
            students.mkdir(parents=True)
            (workspace / "workspace.json").write_text("{}", encoding="utf-8")
            for identifier in ("student01", "student02"):
                report_root = students / identifier
                report_root.mkdir()
                (report_root / "runtime-output.log").write_text("run", encoding="utf-8")
                (report_root / "build-output.log").write_text("build", encoding="utf-8")

            runtime_index = create_runtime_log_index(workspace).directory
            buildtime_index = create_buildtime_log_index(workspace).directory
            self.assertEqual(
                os.readlink(runtime_index / "student01"),
                "../students/student01/runtime-output.log",
            )
            self.assertEqual(
                os.readlink(buildtime_index / "student02"),
                "../students/student02/build-output.log",
            )


if __name__ == "__main__":
    unittest.main()
