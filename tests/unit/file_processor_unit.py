from core.shell import Shell
from core.build import Build
from core.file_processor import FileProcessor
from tools import util

import unittest
from unittest.mock import patch, mock_open, MagicMock
import sys
import subprocess
import os


_fh = "file1.txt"
_fhs = [f"file{i}.txt" for i in range(1, 6)]


def _create_mock_file(name, data="data"):
    """ Helper function to create a mock file with the required attributes. """
    mock_fh = mock_open(read_data=data).return_value
    mock_fh.name = name # file needs name attribute
    mock_fh.close = lambda: None    # file needs close function attribute
    return mock_fh


class TestFileProcessor(unittest.TestCase):
    def test_single_file(self):
        """ Test FileProcessor with a single file """
        processor = FileProcessor(_fh, "r")
        self.assertEqual(processor.files, ["file1.txt"])

    def test_list_of_files(self):
        """ Test FileProcessor with a list of files """
        processor = FileProcessor(_fhs, "r")
        self.assertEqual(processor.files, _fhs)

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
        processor = FileProcessor(_fh, "r")
        fh = next(iter(processor))  # Get the first file handle
        fh.read()  # Ensure file is being read
        fh.close()  # Ensure file handle is closed after use

        # Check if the file was opened correctly
        open.assert_called_with(_fh, "r")
        self.assertTrue(fh)

    @patch("builtins.open", side_effect=FileNotFoundError("non_existent_file.txt"))
    def test_file_not_found(self, mock_open):
        """ Test when a file is not found """
        processor = FileProcessor("non_existent_file.txt", "r")
        with self.assertRaises(FileNotFoundError) as context:
            next(iter(processor))  # This should raise the "File not found" exception.
        self.assertIn("File not found: non_existent_file.txt", str(context.exception))

    @patch("builtins.open", mock_open())
    def test_permission_error(self):
        """ Test when permission is denied to open a file """
        processor = FileProcessor(_fh, "r")
        with patch("builtins.open", side_effect=PermissionError):
            with self.assertRaises(Exception) as context:
                next(iter(processor))
            self.assertIn("Permission denied: file1.txt", str(context.exception))

    @patch("builtins.open", mock_open())
    def test_file_type(self):
        """ Test getting file extension/type """
        processor = FileProcessor(_fh, "r")
        next(iter(processor))  # Process the first file
        file_type = processor.get_type()
        self.assertEqual(file_type, ".txt")

    def test_get_type_no_current_file(self):
        """ Test calling get_type when no file is processed """
        processor = FileProcessor(_fh, "r")
        with self.assertRaises(ValueError):
            processor.get_type()

    def test_iteration(self):
        """ Test iteration over the files """
        mock_fhs = [ _create_mock_file(name) for name in _fhs ]

        with patch("builtins.open", side_effect = mock_fhs):
            processor = FileProcessor(_fhs, "r")
            fhs = [fh.name for fh in processor]
            self.assertEqual(fhs, _fhs)

    def test_iteration_empty(self):
        """ Test iteration when no files are provided """
        processor = FileProcessor([], "r")
        with self.assertRaises(StopIteration):
            next(iter(processor))  # Should immediately raise StopIteration


if __name__ == "__main__":
    unittest.main()
