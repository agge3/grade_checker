"""Unit tests for the CodeAnalyzer integration adapter."""

from pathlib import Path
import tempfile
import unittest

from core.similarity import SimilarityAnalyzer, temporary_source_index
from core.workspace_reporter import WorkspaceReporter


class SimilarityAnalyzerTests(unittest.TestCase):
    """Verify analyzer configuration and source discovery behavior."""

    def test_extracts_hard_coded_config_path(self) -> None:
        """Extract the path used by the supplied C++ analyzer."""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "CodeAnalyzer.cpp"
            source.write_text(
                'const string JSON_FILE = R"(C:\\\\tool\\\\milestone.json)";',
                encoding="utf-8",
            )
            self.assertEqual(
                SimilarityAnalyzer._config_filename(source),
                "C:\\\\tool\\\\milestone.json",
            )

    def test_missing_analyzer_source_is_reported(self) -> None:
        """Reject a path that does not contain CodeAnalyzer.cpp."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                SimilarityAnalyzer(directory)._resolve_source()

    def test_repository_discovery_is_optional(self) -> None:
        """Return a valid analyzer when installed, otherwise return none."""
        analyzer = WorkspaceReporter._find_repository_analyzer()
        if analyzer is not None:
            source = analyzer if analyzer.is_file() else analyzer / "CodeAnalyzer.cpp"
            self.assertTrue(source.is_file())

    def test_temporary_source_index_excludes_student_metadata_and_reports(self) -> None:
        """Ensure CodeAnalyzer staging contains only supported source files."""
        with tempfile.TemporaryDirectory() as directory:
            students = Path(directory) / "students"
            student = students / "alice"
            source_root = student / "src-files"
            source_root.mkdir(parents=True)
            (source_root / "student.cpp").write_text("int main() {}", encoding="utf-8")
            (source_root / "README.md").write_text("student notes", encoding="utf-8")
            (student / "submission_metadata.json").write_text("{}", encoding="utf-8")
            (student / "report.txt").write_text("grade", encoding="utf-8")

            with temporary_source_index(students) as index:
                staged = index / "alice"
                self.assertEqual(
                    [path.name for path in staged.rglob("*") if path.is_file()],
                    ["student.cpp"],
                )
            self.assertFalse(index.exists())


if __name__ == "__main__":
    unittest.main()
