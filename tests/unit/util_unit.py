from tools import util

import unittest
from unittest.mock import patch, MagicMock
import sys
import subprocess
import os


class TestUtil(unittest.TestCase):
    @patch.object(os, 'name', 'nt')
    def test_is_windows_true(self):
        self.assertTrue(util.is_windows())
    
    @patch.object(os, 'name', 'posix')
    def test_is_windows_false(self):
        self.assertFalse(util.is_windows())

    @patch('tools.util.check_file')
    def test_check_files_all_exist(self, mock_check_file):
        mock_check_file.side_effect = [ True, True ]
        result = util.check_files([ "file1.txt", "file2.txt" ])
        self.assertTrue(result)

    @patch('tools.util.check_file')
    def test_check_files_some_dont_exist(self, mock_check_file):
        mock_check_file.side_effect = [True, False]  # First file exists, second doesn't
        result = util.check_files([ "file1.txt", "file2.txt" ])
        self.assertFalse(result)

    @patch('tools.util.check_file')
    def test_check_files_none_exist(self, mock_check_file):
        mock_check_file.side_effect = [ False, False]
        result = util.check_files([ "file1.txt", "file2.txt" ])
        self.assertFalse(result)

    def test_split_clazz_name(self):
        self.assertEqual(util.split_clazz_name("MyClassName"),
            [ 'My', 'Class', 'Name' ])
        self.assertEqual(util.split_clazz_name("TestCase"), [ 'Test', 'Case' ])
        self.assertEqual(util.split_clazz_name("AnotherTest"),
            [ 'Another', 'Test' ])
        # xxx not designed to handle all lowercase, maybe change?
        #self.assertEqual(gc._split_clazz_name("simple"), [ 'simple' ])  # No uppercase letters

    def test_lst_to_str(self):
        lst = ["hi", "hello", "ello"]
        s = util.lst_to_str(lst)
        self.assertEquals(s, "hi hello ello")
        lst = []
        s = util.lst_to_str(lst)
        self.assertEquals(s, "")
        lst = ["hi"]
        s = util.lst_to_str(lst)
        self.assertEquals(s, "hi")


if __name__ == "__main__":
    unittest.main()
