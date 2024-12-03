import grade_checker

import unittest
from unittest.mock import patch, MagicMock
import sys
import subprocess
import os


class TestUtil(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
