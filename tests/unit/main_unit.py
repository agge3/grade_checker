"""Tests for the command-line orchestration layer."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json

import main


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


if __name__ == "__main__":
    unittest.main()
