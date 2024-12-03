import grade_checker

import unittest
from unittest.mock import patch, MagicMock
import sys
import subprocess
import os


class TestFileProcessor(unittest.TestCase):

    def test_single_file(self):
        """ Test FileProcessor with a single file """
        processor = FileProcessor("file1.txt", "r")
        self.assertEqual(processor.files, ["file1.txt"])

    def test_list_of_files(self):
        """ Test FileProcessor with a list of files """
        processor = FileProcessor(["file1.txt", "file2.txt"], "r")
        self.assertEqual(processor.files, ["file1.txt", "file2.txt"])

    def test_nested_list_of_files(self):
        """ Test FileProcessor with a nested list of files """
        processor = FileProcessor([["file1.txt", "file2.txt"], ["file3.txt"]], "r")
        self.assertEqual(processor.files, ["file1.txt", "file2.txt", "file3.txt"])

    def test_invalid_files_type(self):
        """ Test FileProcessor with invalid file type """
        with self.assertRaises(ValueError):
            FileProcessor(123, "r")  # Should raise ValueError

    @patch("builtins.open", mock_open(read_data="data"))
    def test_file_opening(self):
        """ Test the file opening logic """
        processor = FileProcessor("file1.txt", "r")
        fh = next(iter(processor))  # Get the first file handle
        fh.read()  # Ensure file is being read
        fh.close()  # Ensure file handle is closed after use

        # Check if the file was opened correctly
        open.assert_called_with("file1.txt", "r")
        self.assertTrue(fh)

    @patch("builtins.open", mock_open())
    def test_file_not_found(self):
        """ Test when a file is not found """
        processor = FileProcessor("non_existent_file.txt", "r")
        with self.assertRaises(Exception) as context:
            next(iter(processor))  # This should raise the "File not found" exception
        self.assertIn("File not found: non_existent_file.txt", str(context.exception))

    @patch("builtins.open", mock_open())
    def test_permission_error(self):
        """ Test when permission is denied to open a file """
        processor = FileProcessor("file1.txt", "r")
        with patch("builtins.open", side_effect=PermissionError):
            with self.assertRaises(Exception) as context:
                next(iter(processor))
            self.assertIn("Permission denied: file1.txt", str(context.exception))

    @patch("builtins.open", mock_open())
    def test_file_type(self):
        """ Test getting file extension/type """
        processor = FileProcessor("file1.txt", "r")
        next(iter(processor))  # Process the first file
        file_type = processor.get_type()
        self.assertEqual(file_type, ".txt")

    def test_get_type_no_current_file(self):
        """ Test calling get_type when no file is processed """
        processor = FileProcessor("file1.txt", "r")
        with self.assertRaises(ValueError):
            processor.get_type()

    def test_iteration(self):
        """ Test iteration over the files """
        processor = FileProcessor(["file1.txt", "file2.txt"], "r")
        files = [fh.name for fh in processor]
        self.assertEqual(files, ["file1.txt", "file2.txt"])

    def test_iteration_empty(self):
        """ Test iteration when no files are provided """
        processor = FileProcessor([], "r")
        with self.assertRaises(StopIteration):
            next(iter(processor))  # Should immediately raise StopIteration


if __name__ == "__main__":
    unittest.main()
