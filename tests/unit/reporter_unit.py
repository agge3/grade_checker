import grade_checker

import unittest
from unittest.mock import patch, MagicMock
import sys
import subprocess
import os


class TestGradeReporter(unittest.TestCase):

    @patch("shell.Shell.cmd")
    @patch("grader.Grader")
    def test_generate_report_success(self, mock_grader, mock_cmd):
        """ Test report generation when everything works """

        # Mock shell cmd to simulate extra credit score and generic grading
        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score

        # Mock Grader methods to return mock grading scores
        mock_grader_instance = MagicMock()
        mock_grader_instance.check_headers.return_value = 0.75
        mock_grader_instance.check_func.return_value = (0.80, 0.90, 1)
        mock_grader_instance.check_prime.return_value = 1.0
        mock_grader_instance.check_list.return_value = 0.5

        mock_grader.return_value = mock_grader_instance

        # Initialize GradeReporter
        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
        
        # Generate the report
        report = reporter.generate_report()

        # Validate the generated report contents
        self.assertEqual(report["extra_credit_score"], ["85.0"])
        self.assertEqual(report["headers_score"], ["0.75"])
        self.assertEqual(report["functionality_score"], ["0.80"])
        self.assertEqual(report["comments_score"], ["0.90"])
        self.assertEqual(report["class_comment_score"], ["1.00"])
        self.assertEqual(report["prime_score"], ["1.00"])
        self.assertEqual(report["list_score"], ["0.50"])
        self.assertEqual(report["total_score"], ["4.00"])

    @patch("shell.Shell.cmd")
    @patch("grader.Grader")
    def test_generate_report_error_in_func_check(self, mock_grader, mock_cmd):
        """ Test report generation when there is an error in function checking """

        # Mock shell cmd to simulate extra credit score
        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score

        # Mock Grader methods to simulate an error in function checking
        mock_grader_instance = MagicMock()
        mock_grader_instance.check_headers.return_value = 0.75
        mock_grader_instance.check_func.side_effect = Exception("Function check error")
        mock_grader_instance.check_prime.return_value = 1.0
        mock_grader_instance.check_list.return_value = 0.5

        mock_grader.return_value = mock_grader_instance

        # Initialize GradeReporter
        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
        
        # Generate the report
        report = reporter.generate_report()

        # Validate the generated report contents
        self.assertEqual(report["extra_credit_score"], ["85.0"])
        self.assertEqual(report["headers_score"], ["0.75"])
        self.assertEqual(report["functionality_score"], ["Error"])
        self.assertEqual(report["comments_score"], ["Error"])
        self.assertEqual(report["class_comment_score"], ["Error"])
        self.assertEqual(report["prime_score"], ["1.00"])
        self.assertEqual(report["list_score"], ["0.50"])
        self.assertEqual(report["total_score"], ["2.25"])

    @patch("shell.Shell.cmd")
    @patch("grader.Grader")
    def test_generate_report_error_in_check_headers(self, mock_grader, mock_cmd):
        """ Test report generation when there is an error in header checking """

        # Mock shell cmd to simulate extra credit score
        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score

        # Mock Grader methods to simulate an error in header checking
        mock_grader_instance = MagicMock()
        mock_grader_instance.check_headers.side_effect = Exception("Header check error")
        mock_grader_instance.check_func.return_value = (0.80, 0.90, 1)
        mock_grader_instance.check_prime.return_value = 1.0
        mock_grader_instance.check_list.return_value = 0.5

        mock_grader.return_value = mock_grader_instance

        # Initialize GradeReporter
        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
        
        # Generate the report
        report = reporter.generate_report()

        # Validate the generated report contents
        self.assertEqual(report["extra_credit_score"], ["85.0"])
        self.assertEqual(report["headers_score"], ["Error"])
        self.assertEqual(report["functionality_score"], ["0.80"])
        self.assertEqual(report["comments_score"], ["0.90"])
        self.assertEqual(report["class_comment_score"], ["1.00"])
        self.assertEqual(report["prime_score"], ["1.00"])
        self.assertEqual(report["list_score"], ["0.50"])
        self.assertEqual(report["total_score"], ["3.25"])

    @patch("shell.Shell.cmd")
    @patch("grader.Grader")
    @patch("builtins.open", new_callable=MagicMock)
    def test_save_report(self, mock_open, mock_grader, mock_cmd):
        """ Test saving the generated report to a file """

        # Mock shell cmd to simulate extra credit score and grading
        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score

        # Mock Grader methods
        mock_grader_instance = MagicMock()
        mock_grader_instance.check_headers.return_value = 0.75
        mock_grader_instance.check_func.return_value = (0.80, 0.90, 1)
        mock_grader_instance.check_prime.return_value = 1.0
        mock_grader_instance.check_list.return_value = 0.5

        mock_grader.return_value = mock_grader_instance

        # Initialize GradeReporter
        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
        
        # Generate the report
        reporter.generate_report()

        # Simulate saving the report
        mock_open.return_value = MagicMock()
        reporter.save_report("test_report.txt")

        # Check if open() was called with the correct filename
        mock_open.assert_called_with("test_report.txt", "w")

        # Check if write() was called to write the report
        mock_open.return_value.write.assert_any_call('extra_credit_score="85.0"\n')
        mock_open.return_value.write.assert_any_call('headers_score="0.75"\n')
        mock_open.return_value.write.assert_any_call('functionality_score="0.80"\n')
        mock_open.return_value.write.assert_any_call('comments_score="0.90"\n')
        mock_open.return_value.write.assert_any_call('class_comment_score="1.00"\n')
        mock_open.return_value.write.assert_any_call('prime_score="1.00"\n')
        mock_open.return_value.write.assert_any_call('list_score="0.50"\n')
        mock_open.return_value.write.assert_any_call('total_score="4.00"\n')

    @patch("shell.Shell.cmd")
    @patch("grader.Grader")
    def test_save_report_error(self, mock_grader, mock_cmd):
        """ Test saving the report when an error occurs during file write """

        # Mock shell cmd to simulate extra credit score and grading
        mock_cmd.return_value = ("85.0", "", 0)  # Simulate extra credit score

        # Mock Grader methods
        mock_grader_instance = MagicMock()
        mock_grader_instance.check_headers.return_value = 0.75
        mock_grader_instance.check_func.return_value = (0.80, 0.90, 1)
        mock_grader_instance.check_prime.return_value = 1.0
        mock_grader_instance.check_list.return_value = 0.5

        mock_grader.return_value = mock_grader_instance

        # Initialize GradeReporter
        reporter = GradeReporter(shell=MagicMock(), clazz="MyClass")
        
        # Generate the report
        reporter.generate_report()

        # Simulate an error during file writing
        with patch("builtins.open", side_effect=Exception("File write error")):
            with self.assertRaises(Exception):
                reporter.save_report("test_report.txt")


class TestSummaryDisplayer(unittest.TestCase):

    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    @patch("builtins.open", new_callable=MagicMock)
    def test_generate_summary_success(self, mock_open, mock_isfile, mock_isdir, mock_listdir):
        """ Test the summary generation when reports are valid """

        # Mock the filesystem behavior
        mock_listdir.return_value = ["student1", "student2", "student3"]
        mock_isdir.side_effect = lambda path: path in ["student1", "student2", "student3"]
        mock_isfile.side_effect = lambda path: path == "student1/grade_report.txt" or path == "student2/grade_report.txt"
        
        # Mock file contents for valid reports
        mock_open.return_value.__enter__.return_value.readlines.return_value = [
            "total_score=\"85.00\"\n"
        ]
        
        # Initialize SummaryDisplayer
        report_dir = "path_to_reports"
        summary_displayer = SummaryDisplayer(report_dir)

        # Generate summary
        student_scores = summary_displayer.generate_summary()

        # Check that student scores are correct
        self.assertEqual(student_scores["student1"], 85.0)
        self.assertEqual(student_scores["student2"], 85.0)
        self.assertEqual(student_scores["student3"], "No Report")

    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    @patch("builtins.open", new_callable=MagicMock)
    def test_generate_summary_error_in_reading_report(self, mock_open, mock_isfile, mock_isdir, mock_listdir):
        """ Test the summary generation when there is an error reading a report """

        # Mock the filesystem behavior
        mock_listdir.return_value = ["student1", "student2", "student3"]
        mock_isdir.side_effect = lambda path: path in ["student1", "student2", "student3"]
        mock_isfile.side_effect = lambda path: path == "student1/grade_report.txt" or path == "student2/grade_report.txt"
        
        # Simulate an error when reading student2's report
        mock_open.side_effect = [MagicMock(), MagicMock()]
        mock_open.return_value.__enter__.return_value.readlines.side_effect = [
            ["total_score=\"85.00\"\n"],
            Exception("Error reading file")
        ]
        
        # Initialize SummaryDisplayer
        report_dir = "path_to_reports"
        summary_displayer = SummaryDisplayer(report_dir)

        # Generate summary
        student_scores = summary_displayer.generate_summary()

        # Check that student2 has an error recorded
        self.assertEqual(student_scores["student1"], 85.0)
        self.assertEqual(student_scores["student2"], "Error")
        self.assertEqual(student_scores["student3"], "No Report")

    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_generate_summary_no_report_file(self, mock_isfile, mock_isdir, mock_listdir):
        """ Test the summary generation when a report file is missing """

        # Mock the filesystem behavior
        mock_listdir.return_value = ["student1", "student2", "student3"]
        mock_isdir.side_effect = lambda path: path in ["student1", "student2", "student3"]
        mock_isfile.side_effect = lambda path: path == "student1/grade_report.txt"
        
        # Initialize SummaryDisplayer
        report_dir = "path_to_reports"
        summary_displayer = SummaryDisplayer(report_dir)

        # Generate summary
        student_scores = summary_displayer.generate_summary()

        # Check that student3 has "No Report" because the file is missing
        self.assertEqual(student_scores["student1"], 85.0)
        self.assertEqual(student_scores["student2"], "No Report")
        self.assertEqual(student_scores["student3"], "No Report")

    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    @patch("builtins.print")
    def test_display_summary(self, mock_print, mock_isfile, mock_isdir, mock_listdir):
        """ Test the display summary method """

        # Mock the filesystem behavior
        mock_listdir.return_value = ["student1", "student2", "student3"]
        mock_isdir.side_effect = lambda path: path in ["student1", "student2", "student3"]
        mock_isfile.side_effect = lambda path: path == "student1/grade_report.txt" or path == "student2/grade_report.txt"
        
        # Mock file contents for valid reports
        mock_open.return_value.__enter__.return_value.readlines.return_value = [
            "total_score=\"85.00\"\n"
        ]
        
        # Initialize SummaryDisplayer
        report_dir = "path_to_reports"
        summary_displayer = SummaryDisplayer(report_dir)

        # Call the display_summary function
        summary_displayer.display_summary()

        # Check if print was called with the correct output
        mock_print.assert_any_call("Grade Summary Report")
        mock_print.assert_any_call("=====================")
        mock_print.assert_any_call("student1: 85.00")
        mock_print.assert_any_call("student2: 85.00")
        mock_print.assert_any_call("student3: No Report")

    @patch("os.listdir")
    @patch("os.path.isdir")
    @patch("os.path.isfile")
    def test_generate_summary_empty_directory(self, mock_isfile, mock_isdir, mock_listdir):
        """ Test the summary generation with an empty directory """

        # Mock the filesystem behavior
        mock_listdir.return_value = []
        mock_isdir.side_effect = lambda path: False
        mock_isfile.side_effect = lambda path: False
        
        # Initialize SummaryDisplayer
        report_dir = "path_to_reports"
        summary_displayer = SummaryDisplayer(report_dir)

        # Generate summary
        student_scores = summary_displayer.generate_summary()

        # Check that the summary is empty
        self.assertEqual(student_scores, {})


if __name__ == "__main__":
    unittest.main()
