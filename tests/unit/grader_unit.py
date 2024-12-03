class TestGrader(unittest.TestCase):

    @patch("shell.Shell.cmd")
    def test_initializer_files_check(self, mock_cmd):
        """ Test Grader initialization and file checking """

        # Mock the shell command outputs for finding .hpp and .cpp files.
        mock_cmd.return_value = ("/path/to/file1.hpp\n/path/to/file2.hpp", "", 0)
        
        # Initialize Grader instance with a mocked shell and a dummy class name
        grader = Grader(shell=MagicMock(), clazz="MyClass")

        # Verify that files are fetched correctly and check if _check_files is called
        self.assertEqual(grader.files["hpp"], ["/path/to/file1.hpp", "/path/to/file2.hpp"])
        self.assertEqual(grader.files["cpp"], [])

    @patch("shell.Shell.cmd")
    @patch("builtins.print")
    def test_initializer_files_not_found(self, mock_print, mock_cmd):
        """ Test Grader initialization when files cannot be found """

        # Mock the shell command to simulate file not found (empty result)
        mock_cmd.return_value = ("", "", 1)
        
        # Initialize Grader with a non-existent class name
        with self.assertRaises(SystemExit):
            Grader(shell=MagicMock(), clazz="NonExistentClass")

        mock_print.assert_called_with("Grader was unable to find files: {'hpp': [], 'cpp': []}. Exiting...")

    @patch("shell.Shell.cmd")
    @patch("grader.FileProcessor")
    def test_check_func(self, mock_file_processor, mock_cmd):
        """ Test Grader's check_func method """

        # Mock shell cmd to return dummy .hpp and .cpp files
        mock_cmd.return_value = ("/path/to/header.hpp\n", "", 0)

        # Mock FileProcessor to return dummy file handles
        mock_file_processor.return_value.__iter__.return_value = [
            MagicMock(readlines=MagicMock(return_value=["class MyClass {", "HashNode** getTable(", "*/"])),
            MagicMock(read=MagicMock(return_value="int getSize(int a) {"))
        ]

        grader = Grader(shell=MagicMock(), clazz="MyClass")
        func_score, comments_score, clazz_comment = grader.check_func()

        # Validate that the function checking method works and returns correct scores
        self.assertEqual(func_score, 1)
        self.assertEqual(comments_score, 1)
        self.assertEqual(clazz_comment, 1)

    @patch("shell.Shell.cmd")
    @patch("grader.FileProcessor")
    def test_check_headers(self, mock_file_processor, mock_cmd):
        """ Test Grader's check_headers method """

        # Mock shell cmd to return dummy .hpp and .cpp files
        mock_cmd.return_value = ("/path/to/header.hpp\n", "", 0)

        # Mock FileProcessor to return dummy file handles
        mock_file_processor.return_value.__iter__.return_value = [
            MagicMock(readlines=MagicMock(return_value=["/**", "Created by John Doe", "*/"])),
            MagicMock(readlines=MagicMock(return_value=["/**", "Modified by Jane Doe", "*/"]))
        ]

        grader = Grader(shell=MagicMock(), clazz="MyClass")
        score = grader.check_headers()

        # Validate that the header checking logic works correctly
        self.assertEqual(score, 1)

    @patch("shell.Shell.cmd")
    @patch("grader.FileProcessor")
    def test_check_list(self, mock_file_processor, mock_cmd):
        """ Test Grader's check_list method """

        # Mock shell cmd to return dummy .hpp and .cpp files
        mock_cmd.return_value = ("/path/to/list.hpp\n", "", 0)

        # Mock FileProcessor to return dummy file handles
        mock_file_processor.return_value.__iter__.return_value = [
            MagicMock(read=MagicMock(return_value="SinglyLinkedList"))
        ]

        grader = Grader(shell=MagicMock(), clazz="MyClass")
        list_score = grader.check_list()

        # Validate that the check_list method detects list types correctly
        self.assertEqual(list_score, 1)

    @patch("shell.Shell.cmd")
    @patch("grader.FileProcessor")
    def test_check_prime(self, mock_file_processor, mock_cmd):
        """ Test Grader's check_prime method """

        # Mock shell cmd to return dummy .hpp files
        mock_cmd.return_value = ("/path/to/file.hpp\n", "", 0)

        # Mock FileProcessor to return dummy file handles
        mock_file_processor.return_value.__iter__.return_value = [
            MagicMock(read=MagicMock(return_value="HashNode* getItem(int i) { return 3; }"))
        ]

        grader = Grader(shell=MagicMock(), clazz="MyClass")
        prime_score = grader.check_prime()

        # Validate that the check_prime method detects primes correctly
        self.assertEqual(prime_score, 1)

    @patch("shell.Shell.cmd")
    @patch("grader.FileProcessor")
    def test_check_prime_no_prime(self, mock_file_processor, mock_cmd):
        """ Test Grader's check_prime method with no primes """

        # Mock shell cmd to return dummy .hpp files
        mock_cmd.return_value = ("/path/to/file.hpp\n", "", 0)

        # Mock FileProcessor to return dummy file handles
        mock_file_processor.return_value.__iter__.return_value = [
            MagicMock(read=MagicMock(return_value="HashNode* getItem(int i) { return 2; }"))
        ]

        grader = Grader(shell=MagicMock(), clazz="MyClass")
        prime_score = grader.check_prime()

        # Validate that the check_prime method returns 0 when no prime is found
        self.assertEqual(prime_score, 0)

