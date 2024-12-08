from core.build import Build
from tools import util

import unittest
from unittest.mock import patch, MagicMock
import sys
import subprocess
import os
import io


class TestBuild(unittest.TestCase):
    @patch.object(os, 'name', 'nt')
    @patch('os.getenv',
        return_value=r"C:\Program Files (x86);C:\Program Files")
    @patch('os.walk',
        return_value=[
            (r"C:\Program Files", [], [ "msbuild.exe" ]),
            (r"C:\Program Files (x86)", [], [ "msbuild.exe" ])
       ])
    @patch('subprocess.run')
    def test_find_msbuild_win(self, mock_getenv, mock_os_walk, mock_subprocess):
        # Test finding msbuild.exe on Windows.
        build = Build()
        # Redudant on Windows, but double-checking on *Nix.
        path = build.exec_name.replace("/", "\\")
        self.assertEqual(path, r"C:\Program Files\msbuild.exe")


    @patch.object(os, 'name', 'nt')
    @patch('os.getenv',
        return_value=r"C:\Program Files (x86);C:\Program Files")
    # `msbuild.exe` not found in walk.
    @patch('os.walk', return_value=[])
    @patch('sys.stdout', new_callable = io.StringIO)
    def test_find_msbuild_not_found(self, mock_stdout, mock_os_walk, 
                                    mock_getenv):
        # Test when msbuild.exe is not found on Windows.
        with self.assertRaises(SystemExit) as cmd:
            build = Build()
        self.assertEqual(cmd.exception.code, 1)
        self.assertEqual(mock_stdout.getvalue(),
                         "msbuild.exe not found on this system.\n")

    @patch.object(os, 'name', 'nt')
    @patch('core.build.Build._find_msbuild',
           return_value=r"C:\Program Files\msbuild.exe")
    @patch('core.build.subprocess.run')
    def test_find_sln_path_success(self, mock_subprocess, mock_find_msbuild):
        # Test finding the `.sln` file on Windows.
        mock_subprocess.return_value = MagicMock(
            stdout = "path\\to\\project.sln\n",
            stderr = "",
            returncode = 0
        )

        build = Build()
        self.assertEqual(build.config.strip(), "path\\to\\project.sln")

        # Ensure subprocess.run was called as expected.
        mock_subprocess.assert_called_once_with(
            'findstr /S /I ".sln" *',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
    
        @patch.object(os, 'name', 'nt')
        @patch('core.build.Build._find_msbuild',
               return_value=r"C:\Program Files\msbuild.exe")
        @patch('core.build.subprocess.run')
        def test_find_sln_path_no_file(self, mock_subprocess,
                                       mock_find_msbuild):
            # Test when no `.sln` file is found on Windows.
            mock_subprocess.return_value = MagicMock(
                stdout = "",
                stderr = "",
                returncode = 1
            )

            build = Build()
            build.config = build._find_sln_path()
            self.assertIsNone(build.config)

            # Ensure subprocess.run was called as expected.
            mock_subprocess.assert_called_once_with(
                'findstr /S /I ".sln" *',
                shell=True,
                capture_output=True,
                text=True,
                check=True
            )
    
        @patch.object(os, 'name', 'nt')
        @patch('core.build.Build._find_msbuild',
               return_value=r"C:\Program Files\msbuild.exe")
        @patch('core.build.subprocess.run')
        def test_make_run_windows_success(self, mock_subprocess,
                                          mock_find_msbuild):
            # Test building and running the project on Windows.
            mock_subprocess.return_value = MagicMock(
                stdout = "Build successful",
                stderr = "",
                returncode = 0
            )
            
            # Mocking executable in Debug folder.
            with patch('os.listdir', return_value=["project.exe"]):
                build = Build()
                build.cmd = (
                    '"C:\\Program Files\\msbuild.exe" "project.sln" '
                    '/p:Configuration=Debug'
                )
                stdout, succ = build.make_run()
    
            self.assertTrue(succ)
            self.assertIn("Executing: C:\\Project\\Debug\\project.exe", stdout)
    
        @patch.object(os, 'name', 'nt')
        @patch('core.Build.Build._find_msbuild',
               return_value=r"C:\Program Files\msbuild.exe")
        @patch('core.build.subprocess.run')
        def test_make_run_windows_failure(self, mock_subprocess):
            # Test failed build on Windows.
            mock_subprocess.return_value = MagicMock(
                stdout = "Build failed",
                stderr = "",
                returncode = 1
            )
            
            build = Build()
            build.cmd = (
                '"C:\\Program Files\\msbuild.exe" "project.sln" '
                '/p:Configuration=Debug'
            )
            stdout, succ = build.make_run()
    
            self.assertFalse(succ)
            self.assertIn("Build failed with code 1:", stdout)

        @patch.object(os, 'name', 'posix')
        @patch('core.build.subprocess.run')
        def test_make_run_non_windows_success(self, mock_subprocess):
            # Test building and running the project on *Nix systems.
            # Mock subprocess.run for building.
            mock_subprocess.return_value = MagicMock(
                stdout = "Build successful",
                stderr = "",
                returncode = 0
            )
            
            # Mock subprocess.run for running executable.
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "main"
                build = Build()
                build.cmd = "/usr/bin/env cmake"
                stdout, success = build.make_run()
    
            self.assertTrue(success)
            self.assertIn("Build successful", stdout)
    
        @patch.object(os, 'name', 'posix')
        @patch('core.build.subprocess.run')
        def test_make_run_non_windows_failure(self, mock_subprocess):
            # Test failed build on *Nix systems.
            mock_subprocess.return_value = MagicMock(
                stdout = "Build successful",
                stderr = "",
                returncode = 0
            )
    
            build = Build()
            build.cmd = "/usr/bin/env cmake"
            stdout, success = build.make_run()
    
            self.assertFalse(success)
            self.assertIn("Build failed", stdout)


if __name__ == "__main__":
    unittest.main()
