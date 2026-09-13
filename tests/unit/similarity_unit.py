"""Unit tests for the CodeAnalyzer integration adapter."""

from pathlib import Path
import tempfile
import unittest

from core.similarity import SimilarityAnalyzer
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


if __name__ == "__main__":
    unittest.main()
