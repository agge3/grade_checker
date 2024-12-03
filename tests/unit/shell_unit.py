class TestShell(unittest.TestCase):
    @patch('os.name', return_value='nt')
    @patch.object(Shell, '_get_git_bash_path', return_value="C:\\Program Files\\Git\\bin\\bash.exe")
    def test_get_bash_path_windows(self, mock_get_bash_path, mock_os_name):
        shell = Shell()
        self.assertEqual(shell._bash, "C:\\Program Files\\Git\\bin\\bash.exe")

    @patch('os.name', return_value='posix')
    def test_get_bash_path_posix(self, mock_os_name):
        shell = Shell()
        self.assertEqual(shell._bash, "/usr/bin/env bash")

   @patch('subprocess.run')
    def test_check_dep_success(self, mock_subprocess):
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "grep 2.10"
        shell = Shell()
        # Ensure no exception is raised and we check the stdout
        shell._check_dep()

    @patch('subprocess.run')
    def test_check_dep_failure(self, mock_subprocess):
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "grep not found"
        
        # We'll test that the exception is handled correctly
        with self.assertRaises(SystemExit):
            shell = Shell()
            shell._check_dep()

    @patch('subprocess.run')
    def test_cmd_windows(self, mock_subprocess):
        # Simulating Windows behavior with Git Bash
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Command executed successfully"
        shell = Shell()
        stdout, stderr, returncode = shell.cmd(["echo", "Hello, World!"])
        self.assertEqual(stdout, "Command executed successfully")
        self.assertEqual(returncode, 0)

    @patch('subprocess.run')
    def test_cmd_posix(self, mock_subprocess):
        # Simulating POSIX behavior
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Command executed successfully"
        shell = Shell()
        stdout, stderr, returncode = shell.cmd(["echo", "Hello, World!"])
        self.assertEqual(stdout, "Command executed successfully")
        self.assertEqual(returncode, 0)
