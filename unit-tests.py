import grade_checker

import unittest
from unittest.mock import patch, MagicMock
import sys
import subprocess
import os

class TestGlobalFunctions(unittest.TestCase):
    @patch.object(grade_checker.os, 'name', 'nt')
    def test_is_windows_true(self):
        self.assertTrue(grade_checker._is_windows())
    
    @patch.object(grade_checker.os, 'name', 'posix')
    def test_is_windows_false(self):
        self.assertFalse(grade_checker._is_windows())

    @patch('grade_checker._check_file')
    def test_check_files_all_exist(self, mock_check_file):
        mock_check_file.side_effect = [ True, True ]
        result = grade_checker._check_files([ "file1.txt", "file2.txt" ])
        self.assertTrue(result)

    @patch('grade_checker._check_file')
    def test_check_files_some_dont_exist(self, mock_check_file):
        mock_check_file.side_effect = [True, False]  # First file exists, second doesn't
        result = grade_checker._check_files([ "file1.txt", "file2.txt" ])
        self.assertFalse(result)

    @patch('grade_checker._check_file')
    def test_check_files_none_exist(self, mock_check_file):
        mock_check_file.side_effect = [ False, False]
        result = grade_checker._check_files([ "file1.txt", "file2.txt" ])
        self.assertFalse(result)

    def test_split_clazz_name(self):
        self.assertEqual(grade_checker._split_clazz_name("MyClassName"),
            [ 'My', 'Class', 'Name' ])
        self.assertEqual(grade_checker._split_clazz_name("TestCase"), [ 'Test', 'Case' ])
        self.assertEqual(grade_checker._split_clazz_name("AnotherTest"),
            [ 'Another', 'Test' ])
        # xxx not designed to handle all lowercase, maybe change?
        #self.assertEqual(gc._split_clazz_name("simple"), [ 'simple' ])  # No uppercase letters

class TestShell(unittest.TestCase):
    @patch.object(grade_checker.os, 'name', 'nt')
    @patch('grade_checker.Shell._get_git_bash_path',
        return_value="C:\\Program Files\\Git\\bin\\bash.exe")
    def test_get_bash_path_win(self, mock_git_bash_path):
        shell = grade_checker.Shell()
        self.assertEqual(shell._bash, "C:\\Program Files\\Git\\bin\\bash.exe")

    @patch.object(grade_checker.os, 'name', 'posix')
    def test_get_bash_path_nix(self):
        shell = grade_checker.Shell()
        self.assertEqual(shell._bash, "/usr/bin/env bash")

    @patch('subprocess.run')
    def test_check_dep_success(self, mock_subprocess):
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "grep 2.10"

        shell = grade_checker.Shell()
        # Ensure no exception is raised when we check stdout.
        shell._check_dep()

    @patch('subprocess.run')
    def test_check_dep_failure(self, mock_subprocess):
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "grep not found"
       
        # Test that exception is raised properly.
        with self.assertRaises(RuntimeError):
            shell = grade_checker.Shell()
            shell._check_dep()

    @patch('subprocess.run')
    def test_cmd_win(self, mock_subprocess):
        # Simulating Windows behavior with Git Bash.
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Command executed successfully"

        shell = grade_checker.Shell()
        stdout, stderr, returncode = shell.cmd(["echo", "Hello, World!"])
        self.assertEqual(stdout, "Command executed successfully")
        self.assertEqual(returncode, 0)

    @patch('subprocess.run')
    def test_cmd_nix(self, mock_subprocess):
        # Simulating POSIX behavior.
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Command executed successfully"

        shell = grade_checker.Shell()
        stdout, stderr, returncode = shell.cmd("echo \"Hello, World!\"")
        self.assertEqual(stdout, "Command executed successfully")
        self.assertEqual(returncode, 0)


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


#class TestFileProcessor(unittest.TestCase):
#
#    def test_single_file(self):
#        """ Test FileProcessor with a single file """
#        processor = FileProcessor("file1.txt", "r")
#        self.assertEqual(processor.files, ["file1.txt"])
#
#    def test_list_of_files(self):
#        """ Test FileProcessor with a list of files """
#        processor = FileProcessor(["file1.txt", "file2.txt"], "r")
#        self.assertEqual(processor.files, ["file1.txt", "file2.txt"])
#
#    def test_nested_list_of_files(self):
#        """ Test FileProcessor with a nested list of files """
#        processor = FileProcessor([["file1.txt", "file2.txt"], ["file3.txt"]], "r")
#        self.assertEqual(processor.files, ["file1.txt", "file2.txt", "file3.txt"])
#
#    def test_invalid_files_type(self):
#        """ Test FileProcessor with invalid file type """
#        with self.assertRaises(ValueError):
#            FileProcessor(123, "r")  # Should raise ValueError
#
#    @patch("builtins.open", mock_open(read_data="data"))
#    def test_file_opening(self):
#        """ Test the file opening logic """
#        processor = FileProcessor("file1.txt", "r")
#        fh = next(iter(processor))  # Get the first file handle
#        fh.read()  # Ensure file is being read
#        fh.close()  # Ensure file handle is closed after use
#
#        # Check if the file was opened correctly
#        open.assert_called_with("file1.txt", "r")
#        self.assertTrue(fh)
#
#    @patch("builtins.open", mock_open())
#    def test_file_not_found(self):
#        """ Test when a file is not found """
#        processor = FileProcessor("non_existent_file.txt", "r")
#        with self.assertRaises(Exception) as context:
#            next(iter(processor))  # This should raise the "File not found" exception
#        self.assertIn("File not found: non_existent_file.txt", str(context.exception))
#
#    @patch("builtins.open", mock_open())
#    def test_permission_error(self):
#        """ Test when permission is denied to open a file """
#        processor = FileProcessor("file1.txt", "r")
#        with patch("builtins.open", side_effect=PermissionError):
#            with self.assertRaises(Exception) as context:
#                next(iter(processor))
#            self.assertIn("Permission denied: file1.txt", str(context.exception))
#
#    @patch("builtins.open", mock_open())
#    def test_file_type(self):
#        """ Test getting file extension/type """
#        processor = FileProcessor("file1.txt", "r")
#        next(iter(processor))  # Process the first file
#        file_type = processor.get_type()
#        self.assertEqual(file_type, ".txt")
#
#    def test_get_type_no_current_file(self):
#        """ Test calling get_type when no file is processed """
#        processor = FileProcessor("file1.txt", "r")
#        with self.assertRaises(ValueError):
#            processor.get_type()
#
#    def test_iteration(self):
#        """ Test iteration over the files """
#        processor = FileProcessor(["file1.txt", "file2.txt"], "r")
#        files = [fh.name for fh in processor]
#        self.assertEqual(files, ["file1.txt", "file2.txt"])
#
#    def test_iteration_empty(self):
#        """ Test iteration when no files are provided """
#        processor = FileProcessor([], "r")
#        with self.assertRaises(StopIteration):
#            next(iter(processor))  # Should immediately raise StopIteration
#
#
#class TestGrader(unittest.TestCase):
#
#    @patch("shell.Shell.cmd")
#    def test_initializer_files_check(self, mock_cmd):
#        """ Test Grader initialization and file checking """
#
#        # Mock the shell command outputs for finding .hpp and .cpp files.
#        mock_cmd.return_value = ("/path/to/file1.hpp\n/path/to/file2.hpp", "", 0)
#        
#        # Initialize Grader instance with a mocked shell and a dummy class name
#        grader = Grader(shell=MagicMock(), clazz="MyClass")
#
#        # Verify that files are fetched correctly and check if _check_files is called
#        self.assertEqual(grader.files["hpp"], ["/path/to/file1.hpp", "/path/to/file2.hpp"])
#        self.assertEqual(grader.files["cpp"], [])
#
#    @patch("shell.Shell.cmd")
#    @patch("builtins.print")
#    def test_initializer_files_not_found(self, mock_print, mock_cmd):
#        """ Test Grader initialization when files cannot be found """
#
#        # Mock the shell command to simulate file not found (empty result)
#        mock_cmd.return_value = ("", "", 1)
#        
#        # Initialize Grader with a non-existent class name
#        with self.assertRaises(SystemExit):
#            Grader(shell=MagicMock(), clazz="NonExistentClass")
#
#        mock_print.assert_called_with("Grader was unable to find files: {'hpp': [], 'cpp': []}. Exiting...")
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.FileProcessor")
#    def test_check_func(self, mock_file_processor, mock_cmd):
#        """ Test Grader's check_func method """
#
#        # Mock shell cmd to return dummy .hpp and .cpp files
#        mock_cmd.return_value = ("/path/to/header.hpp\n", "", 0)
#
#        # Mock FileProcessor to return dummy file handles
#        mock_file_processor.return_value.__iter__.return_value = [
#            MagicMock(readlines=MagicMock(return_value=["class MyClass {", "HashNode** getTable(", "*/"])),
#            MagicMock(read=MagicMock(return_value="int getSize(int a) {"))
#        ]
#
#        grader = Grader(shell=MagicMock(), clazz="MyClass")
#        func_score, comments_score, clazz_comment = grader.check_func()
#
#        # Validate that the function checking method works and returns correct scores
#        self.assertEqual(func_score, 1)
#        self.assertEqual(comments_score, 1)
#        self.assertEqual(clazz_comment, 1)
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.FileProcessor")
#    def test_check_headers(self, mock_file_processor, mock_cmd):
#        """ Test Grader's check_headers method """
#
#        # Mock shell cmd to return dummy .hpp and .cpp files
#        mock_cmd.return_value = ("/path/to/header.hpp\n", "", 0)
#
#        # Mock FileProcessor to return dummy file handles
#        mock_file_processor.return_value.__iter__.return_value = [
#            MagicMock(readlines=MagicMock(return_value=["/**", "Created by John Doe", "*/"])),
#            MagicMock(readlines=MagicMock(return_value=["/**", "Modified by Jane Doe", "*/"]))
#        ]
#
#        grader = Grader(shell=MagicMock(), clazz="MyClass")
#        score = grader.check_headers()
#
#        # Validate that the header checking logic works correctly
#        self.assertEqual(score, 1)
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.FileProcessor")
#    def test_check_list(self, mock_file_processor, mock_cmd):
#        """ Test Grader's check_list method """
#
#        # Mock shell cmd to return dummy .hpp and .cpp files
#        mock_cmd.return_value = ("/path/to/list.hpp\n", "", 0)
#
#        # Mock FileProcessor to return dummy file handles
#        mock_file_processor.return_value.__iter__.return_value = [
#            MagicMock(read=MagicMock(return_value="SinglyLinkedList"))
#        ]
#
#        grader = Grader(shell=MagicMock(), clazz="MyClass")
#        list_score = grader.check_list()
#
#        # Validate that the check_list method detects list types correctly
#        self.assertEqual(list_score, 1)
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.FileProcessor")
#    def test_check_prime(self, mock_file_processor, mock_cmd):
#        """ Test Grader's check_prime method """
#
#        # Mock shell cmd to return dummy .hpp files
#        mock_cmd.return_value = ("/path/to/file.hpp\n", "", 0)
#
#        # Mock FileProcessor to return dummy file handles
#        mock_file_processor.return_value.__iter__.return_value = [
#            MagicMock(read=MagicMock(return_value="HashNode* getItem(int i) { return 3; }"))
#        ]
#
#        grader = Grader(shell=MagicMock(), clazz="MyClass")
#        prime_score = grader.check_prime()
#
#        # Validate that the check_prime method detects primes correctly
#        self.assertEqual(prime_score, 1)
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.FileProcessor")
#    def test_check_prime_no_prime(self, mock_file_processor, mock_cmd):
#        """ Test Grader's check_prime method with no primes """
#
#        # Mock shell cmd to return dummy .hpp files
#        mock_cmd.return_value = ("/path/to/file.hpp\n", "", 0)
#
#        # Mock FileProcessor to return dummy file handles
#        mock_file_processor.return_value.__iter__.return_value = [
#            MagicMock(read=MagicMock(return_value="HashNode* getItem(int i) { return 2; }"))
#        ]
#
#        grader = Grader(shell=MagicMock(), clazz="MyClass")
#        prime_score = grader.check_prime()
#
#        # Validate that the check_prime method returns 0 when no prime is found
#        self.assertEqual(prime_score, 0)
#
#class TestGradeReporter(unittest.TestCase):
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.Grader")
#    def test_generate_report_success(self, mock_grader, mock_cmd):
#        """ Test report generation when everything works """
#
#        # Mock shell cmd to simulate extra credit score and generic grading
#        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score
#
#        # Mock Grader methods to return mock grading scores
#        mock_grader_instance = MagicMock()
#        mock_grader_instance.check_headers.return_value = 0.75
#        mock_grader_instance.check_func.return_value = (0.80, 0.90, 1)
#        mock_grader_instance.check_prime.return_value = 1.0
#        mock_grader_instance.check_list.return_value = 0.5
#
#        mock_grader.return_value = mock_grader_instance
#
#        # Initialize GradeReporter
#        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
#        
#        # Generate the report
#        report = reporter.generate_report()
#
#        # Validate the generated report contents
#        self.assertEqual(report["extra_credit_score"], ["85.0"])
#        self.assertEqual(report["headers_score"], ["0.75"])
#        self.assertEqual(report["functionality_score"], ["0.80"])
#        self.assertEqual(report["comments_score"], ["0.90"])
#        self.assertEqual(report["class_comment_score"], ["1.00"])
#        self.assertEqual(report["prime_score"], ["1.00"])
#        self.assertEqual(report["list_score"], ["0.50"])
#        self.assertEqual(report["total_score"], ["4.00"])
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.Grader")
#    def test_generate_report_error_in_func_check(self, mock_grader, mock_cmd):
#        """ Test report generation when there is an error in function checking """
#
#        # Mock shell cmd to simulate extra credit score
#        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score
#
#        # Mock Grader methods to simulate an error in function checking
#        mock_grader_instance = MagicMock()
#        mock_grader_instance.check_headers.return_value = 0.75
#        mock_grader_instance.check_func.side_effect = Exception("Function check error")
#        mock_grader_instance.check_prime.return_value = 1.0
#        mock_grader_instance.check_list.return_value = 0.5
#
#        mock_grader.return_value = mock_grader_instance
#
#        # Initialize GradeReporter
#        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
#        
#        # Generate the report
#        report = reporter.generate_report()
#
#        # Validate the generated report contents
#        self.assertEqual(report["extra_credit_score"], ["85.0"])
#        self.assertEqual(report["headers_score"], ["0.75"])
#        self.assertEqual(report["functionality_score"], ["Error"])
#        self.assertEqual(report["comments_score"], ["Error"])
#        self.assertEqual(report["class_comment_score"], ["Error"])
#        self.assertEqual(report["prime_score"], ["1.00"])
#        self.assertEqual(report["list_score"], ["0.50"])
#        self.assertEqual(report["total_score"], ["2.25"])
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.Grader")
#    def test_generate_report_error_in_check_headers(self, mock_grader, mock_cmd):
#        """ Test report generation when there is an error in header checking """
#
#        # Mock shell cmd to simulate extra credit score
#        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score
#
#        # Mock Grader methods to simulate an error in header checking
#        mock_grader_instance = MagicMock()
#        mock_grader_instance.check_headers.side_effect = Exception("Header check error")
#        mock_grader_instance.check_func.return_value = (0.80, 0.90, 1)
#        mock_grader_instance.check_prime.return_value = 1.0
#        mock_grader_instance.check_list.return_value = 0.5
#
#        mock_grader.return_value = mock_grader_instance
#
#        # Initialize GradeReporter
#        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
#        
#        # Generate the report
#        report = reporter.generate_report()
#
#        # Validate the generated report contents
#        self.assertEqual(report["extra_credit_score"], ["85.0"])
#        self.assertEqual(report["headers_score"], ["Error"])
#        self.assertEqual(report["functionality_score"], ["0.80"])
#        self.assertEqual(report["comments_score"], ["0.90"])
#        self.assertEqual(report["class_comment_score"], ["1.00"])
#        self.assertEqual(report["prime_score"], ["1.00"])
#        self.assertEqual(report["list_score"], ["0.50"])
#        self.assertEqual(report["total_score"], ["3.25"])
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.Grader")
#    @patch("builtins.open", new_callable=MagicMock)
#    def test_save_report(self, mock_open, mock_grader, mock_cmd):
#        """ Test saving the generated report to a file """
#
#        # Mock shell cmd to simulate extra credit score and grading
#        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score
#
#        # Mock Grader methods
#        mock_grader_instance = MagicMock()
#        mock_grader_instance.check_headers.return_value = 0.75
#        mock_grader_instance.check_func.return_value = (0.80, 0.90, 1)
#        mock_grader_instance.check_prime.return_value = 1.0
#        mock_grader_instance.check_list.return_value = 0.5
#
#        mock_grader.return_value = mock_grader_instance
#
#        # Initialize GradeReporter
#        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
#        
#        # Generate the report
#        reporter.generate_report()
#
#        # Simulate saving the report
#        mock_open.return_value = MagicMock()
#        reporter.save_report("test_report.txt")
#
#        # Check if open() was called with the correct filename
#        mock_open.assert_called_with("test_report.txt", "w")
#
#        # Check if write() was called to write the report
#        mock_open.return_value.write.assert_any_call('extra_credit_score="85.0"\n')
#        mock_open.return_value.write.assert_any_call('headers_score="0.75"\n')
#        mock_open.return_value.write.assert_any_call('functionality_score="0.80"\n')
#        mock_open.return_value.write.assert_any_call('comments_score="0.90"\n')
#        mock_open.return_value.write.assert_any_call('class_comment_score="1.00"\n')
#        mock_open.return_value.write.assert_any_call('prime_score="1.00"\n')
#        mock_open.return_value.write.assert_any_call('list_score="0.50"\n')
#        mock_open.return_value.write.assert_any_call('total_score="4.00"\n')
#
#    @patch("shell.Shell.cmd")
#    @patch("grader.Grader")
#    def test_save_report_error(self, mock_grader, mock_cmd):
#        """ Test saving the report when an error occurs during file write """
#
#        # Mock shell cmd to simulate extra credit score and grading
#        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score
#
#        # Mock Grader methods
#        mock_grader_instance = MagicMock()
#        mock_grader_instance.check_headers.return_value = 0.75
#        mock_grader_instance.check_func.return_value = (0.80, 0.90, 1)
#        mock_grader_instance.check_prime.return_value = 1.0
#        mock_grader_instance.check_list.return_value = 0.5
#
#        mock_grader.return_value = mock_grader_instance
#
#        # Initialize GradeReporter
#        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
#        
#        # Generate the report
#        reporter.generate_report()
#
#        # Simulate an error during file writing
#        with patch("builtins.open", side_effect=Exception("File write error")):
#            with self.assertRaises(Exception):
#                reporter.save_report("test_report.txt")
#
#
#class TestSummaryDisplayer(unittest.TestCase):
#
#    @patch("os.listdir")
#    @patch("os.path.isdir")
#    @patch("os.path.isfile")
#    @patch("builtins.open", new_callable=MagicMock)
#    def test_generate_summary_success(self, mock_open, mock_isfile, mock_isdir, mock_listdir):
#        """ Test the summary generation when reports are valid """
#
#        # Mock the filesystem behavior
#        mock_listdir.return_value = ["student1", "student2", "student3"]
#        mock_isdir.side_effect = lambda path: path in ["student1", "student2", "student3"]
#        mock_isfile.side_effect = lambda path: path == "student1/grade_report.txt" or path == "student2/grade_report.txt"
#        
#        # Mock file contents for valid reports
#        mock_open.return_value.__enter__.return_value.readlines.return_value = [
#            "total_score=\"85.00\"\n"
#        ]
#        
#        # Initialize SummaryDisplayer
#        report_dir = "path_to_reports"
#        summary_displayer = SummaryDisplayer(report_dir)
#
#        # Generate summary
#        student_scores = summary_displayer.generate_summary()
#
#        # Check that student scores are correct
#        self.assertEqual(student_scores["student1"], 85.0)
#        self.assertEqual(student_scores["student2"], 85.0)
#        self.assertEqual(student_scores["student3"], "No Report")
#
#    @patch("os.listdir")
#    @patch("os.path.isdir")
#    @patch("os.path.isfile")
#    @patch("builtins.open", new_callable=MagicMock)
#    def test_generate_summary_error_in_reading_report(self, mock_open, mock_isfile, mock_isdir, mock_listdir):
#        """ Test the summary generation when there is an error reading a report """
#
#        # Mock the filesystem behavior
#        mock_listdir.return_value = ["student1", "student2", "student3"]
#        mock_isdir.side_effect = lambda path: path in ["student1", "student2", "student3"]
#        mock_isfile.side_effect = lambda path: path == "student1/grade_report.txt" or path == "student2/grade_report.txt"
#        
#        # Simulate an error when reading student2's report
#        mock_open.side_effect = [MagicMock(), MagicMock()]
#        mock_open.return_value.__enter__.return_value.readlines.side_effect = [
#            ["total_score=\"85.00\"\n"],
#            Exception("Error reading file")
#        ]
#        
#        # Initialize SummaryDisplayer
#        report_dir = "path_to_reports"
#        summary_displayer = SummaryDisplayer(report_dir)
#
#        # Generate summary
#        student_scores = summary_displayer.generate_summary()
#
#        # Check that student2 has an error recorded
#        self.assertEqual(student_scores["student1"], 85.0)
#        self.assertEqual(student_scores["student2"], "Error")
#        self.assertEqual(student_scores["student3"], "No Report")
#
#    @patch("os.listdir")
#    @patch("os.path.isdir")
#    @patch("os.path.isfile")
#    def test_generate_summary_no_report_file(self, mock_isfile, mock_isdir, mock_listdir):
#        """ Test the summary generation when a report file is missing """
#
#        # Mock the filesystem behavior
#        mock_listdir.return_value = ["student1", "student2", "student3"]
#        mock_isdir.side_effect = lambda path: path in ["student1", "student2", "student3"]
#        mock_isfile.side_effect = lambda path: path == "student1/grade_report.txt"
#        
#        # Initialize SummaryDisplayer
#        report_dir = "path_to_reports"
#        summary_displayer = SummaryDisplayer(report_dir)
#
#        # Generate summary
#        student_scores = summary_displayer.generate_summary()
#
#        # Check that student3 has "No Report" because the file is missing
#        self.assertEqual(student_scores["student1"], 85.0)
#        self.assertEqual(student_scores["student2"], "No Report")
#        self.assertEqual(student_scores["student3"], "No Report")
#
#    @patch("os.listdir")
#    @patch("os.path.isdir")
#    @patch("os.path.isfile")
#    @patch("builtins.print")
#    def test_display_summary(self, mock_print, mock_isfile, mock_isdir, mock_listdir):
#        """ Test the display summary method """
#
#        # Mock the filesystem behavior
#        mock_listdir.return_value = ["student1", "student2", "student3"]
#        mock_isdir.side_effect = lambda path: path in ["student1", "student2", "student3"]
#        mock_isfile.side_effect = lambda path: path == "student1/grade_report.txt" or path == "student2/grade_report.txt"
#        
#        # Mock file contents for valid reports
#        mock_open.return_value.__enter__.return_value.readlines.return_value = [
#            "total_score=\"85.00\"\n"
#        ]
#        
#        # Initialize SummaryDisplayer
#        report_dir = "path_to_reports"
#        summary_displayer = SummaryDisplayer(report_dir)
#
#        # Call the display_summary function
#        summary_displayer.display_summary()
#
#        # Check if print was called with the correct output
#        mock_print.assert_any_call("Grade Summary Report")
#        mock_print.assert_any_call("=====================")
#        mock_print.assert_any_call("student1: 85.00")
#        mock_print.assert_any_call("student2: 85.00")
#        mock_print.assert_any_call("student3: No Report")
#
#    @patch("os.listdir")
#    @patch("os.path.isdir")
#    @patch("os.path.isfile")
#    def test_generate_summary_empty_directory(self, mock_isfile, mock_isdir, mock_listdir):
#        """ Test the summary generation with an empty directory """
#
#        # Mock the filesystem behavior
#        mock_listdir.return_value = []
#        mock_isdir.side_effect = lambda path: False
#        mock_isfile.side_effect = lambda path: False
#        
#        # Initialize SummaryDisplayer
#        report_dir = "path_to_reports"
#        summary_displayer = SummaryDisplayer(report_dir)
#
#        # Generate summary
#        student_scores = summary_displayer.generate_summary()
#
#        # Check that the summary is empty
#        self.assertEqual(student_scores, {})

if __name__ == "__main__":
    unittest.main()
