import grade_checker

import unittest
from unittest.mock import patch, MagicMock
import sys
import subprocess
import os

class TestBuild(unittest.TestCase):
    @patch.object(grade_checker.os, 'name', 'nt')
    @patch('grade_checker.os.getenv',
        return_value=r"C:\Program Files (x86);C:\Program Files")
    @patch('grade_checker.os.walk',
        return_value=[
            (r"C:\Program Files", [], [ "msbuild.exe" ]),
            (r"C:\Program Files (x86)", [], [ "msbuild.exe" ])
       ])
    @patch('subprocess.run')
    def test_find_msbuild_win(self, mock_getenv, mock_os_walk, mock_subprocess):
        # Test finding msbuild.exe on Windows.
        build = grade_checker.Build()
        # Redudant on Windows, but double-checking on *Nix.
        path = build.exec_name.replace("/", "\\")
        self.assertEqual(path, r"C:\Program Files\msbuild.exe")


    @patch.object(grade_checker.os, 'name', 'nt')
    @patch('grade_checker.os.getenv',
        return_value=r"C:\Program Files (x86);C:\Program Files")
    # `msbuild.exe` not found in walk.
    @patch('grade_checker.os.walk', return_value=[])
    @patch('grade_checker.subprocess.run')
    def test_find_msbuild_not_found(self, mock_getenv, mock_os_walk, mock_subprocess):
        # Test when msbuild.exe is not found on Windows.
        mock_subprocess.return_value.returncode = 0
        with self.assertRaises(FileNotFoundError):
            build = grade_checker.Build()  # This should raise FileNotFoundError.


    @patch.object(grade_checker.os, 'name', 'nt')
    @patch('grade_checker.subprocess.run')
    @patch('grade_checker.Build._find_msbuild',
           return_value=r"C:\Program Files\msbuild.exe")
    def test_find_sln_path_success(self, mock_subprocess, mock_find_msbuild):
        # Test finding the `.sln` file on Windows.
        #mock_process = MagicMock()
        #mock_subprocess.stdout = "path\\to\\project.sln\n"
        #mock_subprocess.stderr = ""
        #mock_subprocess.returncode = 0
        #mock_subprocess.return_value = mock_process
        mock_subprocess = MagicMock(
            stdout = "path\\to\\project.sln",
            stderr = "",
            returncode = 0
        )
        print(f"mock ret: {mock_subprocess.stdout}")

        build = grade_checker.Build()
        print(f"mock build ret: {build.config}")

        # Check the results
        self.assertEqual(build.config, "path\\to\\project.sln")
        # Ensure subprocess.run was called as expected
        mock_subprocess.assert_called_once_with(
            'findstr /S /I ".sln" *',
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )

    @patch.object(grade_checker.os, 'name', 'nt')
    @patch('grade_checker.subprocess.run')
    @patch('grade_checker.Build._find_msbuild',
           return_value=r"C:\Program Files\msbuild.exe")
    def test_find_sln_path_no_file(self, mock_subprocess, mock_find_msbuild):
        # Test when no `.sln` file is found on Windows.
        mock_subprocess.return_value.returncode = 1
        build = grade_checker.Build()
        build.config = build._find_sln_path()
        self.assertIsNone(build.config)

    @patch.object(grade_checker.os, 'name', 'nt')
    @patch('grade_checker.subprocess.run')
    @patch('grade_checker.Build._find_msbuild',
           return_value=r"C:\Program Files\msbuild.exe")
    def test_make_run_windows_success(self, mock_subprocess):
        # Test building and running the project on Windows.
        # Mocking successful subprocess run for building
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Build successful"
        
        # Mocking executable in Debug folder.
        with patch('os.listdir', return_value=["project.exe"]):
            build = grade_checker.Build()
            build.cmd = '"C:\\Program Files\\msbuild.exe" "project.sln" ' + \
                '/p:Configuration=Debug'
            stdout, success = build.make_run()

        self.assertTrue(success)
        self.assertIn("Executing: C:\\Project\\Debug\\project.exe", stdout)

    @patch.object(grade_checker.os, 'name', 'nt')
    @patch('grade_checker.subprocess.run')
    @patch('grade_checker.Build._find_msbuild',
           return_value=r"C:\Program Files\msbuild.exe")
    def test_make_run_windows_failure(self, mock_subprocess):
        # Test failed build on Windows.
        # Mocking failed subprocess run for building.
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Build failed"
        
        build = grade_checker.Build()
        build.cmd = '"C:\\Program Files\\msbuild.exe" "project.sln"' + \
            '/p:Configuration=Debug'
        stdout, success = build.make_run()

        self.assertFalse(success)
        self.assertIn("Build failed with code 1:", stdout)

    @patch.object(grade_checker.os, 'name', 'posix')
    @patch('grade_checker.subprocess.run')
    def test_make_run_non_windows_success(self, mock_subprocess):
        # Test building and running the project on *Nix systems.
        # Mocking successful subprocess run for building.
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Build successful"
        
        # Mocking the executable name from cmake build.
        with patch('grade_checker.subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "main"
            build = grade_checker.Build()
            build.cmd = "/usr/bin/env cmake"
            stdout, success = build.make_run()

        self.assertTrue(success)
        self.assertIn("Build successful", stdout)

    @patch.object(grade_checker.os, 'name', 'posix')
    @patch('grade_checker.subprocess.run')
    def test_make_run_non_windows_failure(self, mock_subprocess):
        # Test failed build on *Nix systems.
        # Mocking failed subprocess run for building.
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Build failed"

        build = grade_checker.Build()
        build.cmd = "/usr/bin/env cmake"
        stdout, success = build.make_run()

        self.assertFalse(success)
        self.assertIn("Build failed", stdout)


if __name__ == "__main__":
    unittest.main()
