from core.shell import Shell
from tools import util

import unittest
from unittest.mock import patch, MagicMock
import sys
import subprocess
import os


class TestShell(unittest.TestCase):
    @patch.object(os, 'name', 'nt')
    @patch('core.shell.Shell._get_git_bash_path',
        return_value="C:\\Program Files\\Git\\bin\\bash.exe")
    def test_get_bash_path_win(self, mock_git_bash_path):
        shell = Shell()
        self.assertEqual(shell._bash, "C:\\Program Files\\Git\\bin\\bash.exe")

    @patch.object(os, 'name', 'posix')
    def test_get_bash_path_nix(self):
        shell = Shell()
        self.assertEqual(shell._bash, "/usr/bin/env bash")

    @patch('subprocess.run')
    def test_check_dep_success(self, mock_subprocess):
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "grep 2.10"

        shell = Shell()
        # Ensure no exception is raised when we check stdout.
        shell._check_dep()

    @patch('subprocess.run')
    def test_check_dep_failure(self, mock_subprocess):
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "grep not found"
       
        # Test that exception is raised properly.
        with self.assertRaises(RuntimeError):
            shell = Shell()
            shell._check_dep()

    @patch('subprocess.run')
    def test_cmd_win(self, mock_subprocess):
        # Simulating Windows behavior with Git Bash.
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Command executed successfully"

        shell = Shell()
        stdout, stderr, returncode = shell.cmd(["echo", "Hello, World!"])
        self.assertEqual(stdout, "Command executed successfully")
        self.assertEqual(returncode, 0)

    @patch('subprocess.run')
    def test_cmd_nix(self, mock_subprocess):
        # Simulating POSIX behavior.
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Command executed successfully"

        shell = Shell()
        stdout, stderr, returncode = shell.cmd("echo \"Hello, World!\"")
        self.assertEqual(stdout, "Command executed successfully")
        self.assertEqual(returncode, 0)


if __name__ == "__main__":
    unittest.main()
