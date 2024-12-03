class TestBuild(unittest.TestCase):
    @patch('os.name', return_value='nt')  # Mocking the OS to simulate Windows
    @patch('subprocess.run')
    @patch('os.walk')
    @patch('os.getenv')
    def test_find_msbuild_windows(self, mock_getenv, mock_os_walk, mock_subprocess):
        """ Test finding msbuild.exe on Windows """
        mock_getenv.return_value = r"C:\Program Files (x86);C:\Program Files"
        mock_os_walk.return_value = [
            (r"C:\Program Files", [], ["msbuild.exe"]),
            (r"C:\Program Files (x86)", [], ["msbuild.exe"]),
        ]
        build = Build()
        self.assertEqual(build.exec_name, r"C:\Program Files\msbuild.exe")

    @patch('os.name', return_value='nt')
    @patch('subprocess.run')
    @patch('os.walk')
    @patch('os.getenv')
    def test_find_msbuild_not_found(self, mock_getenv, mock_os_walk, mock_subprocess):
        """ Test when msbuild.exe is not found on Windows """
        mock_getenv.return_value = r"C:\Program Files (x86);C:\Program Files"
        mock_os_walk.return_value = []
        mock_subprocess.return_value.returncode = 0
        with self.assertRaises(FileNotFoundError):
            build = Build()  # This should raise FileNotFoundError

    @patch('os.name', return_value='nt')  # Mocking the OS to simulate Windows
    @patch('subprocess.run')
    def test_find_sln_path_success(self, mock_subprocess):
        """ Test finding the .sln file on Windows """
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "path\\to\\project.sln"
        build = Build()
        build.config = build._find_sln_path()
        self.assertEqual(build.config, "path\\to\\project.sln")

    @patch('os.name', return_value='nt')
    @patch('subprocess.run')
    def test_find_sln_path_no_file(self, mock_subprocess):
        """ Test when no .sln file is found on Windows """
        mock_subprocess.return_value.returncode = 1
        build = Build()
        build.config = build._find_sln_path()
        self.assertIsNone(build.config)

    @patch('os.name', return_value='nt')  # Mocking Windows environment
    @patch('subprocess.run')
    def test_make_run_windows_success(self, mock_subprocess):
        """ Test building and running the project on Windows """
        # Mocking successful subprocess run for building
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Build successful"
        
        # Mocking executable in Debug folder
        with patch('os.listdir', return_value=["project.exe"]):
            build = Build()
            build.cmd = '"C:\\Program Files\\msbuild.exe" "project.sln" /p:Configuration=Debug'
            stdout, success = build.make_run()

        self.assertTrue(success)
        self.assertIn("Executing: C:\\Project\\Debug\\project.exe", stdout)

    @patch('os.name', return_value='nt')  # Mocking Windows environment
    @patch('subprocess.run')
    def test_make_run_windows_failure(self, mock_subprocess):
        """ Test failed build on Windows """
        # Mocking failed subprocess run for building
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Build failed"
        
        build = Build()
        build.cmd = '"C:\\Program Files\\msbuild.exe" "project.sln" /p:Configuration=Debug'
        stdout, success = build.make_run()

        self.assertFalse(success)
        self.assertIn("Build failed with code 1:", stdout)

    @patch('os.name', return_value='posix')  # Mocking Linux/Mac environment
    @patch('subprocess.run')
    def test_make_run_non_windows_success(self, mock_subprocess):
        """ Test building and running the project on a non-Windows system (Linux/Mac) """
        # Mocking successful subprocess run for building
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Build successful"
        
        # Mocking the executable name from cmake build
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "main"
            build = Build()
            build.cmd = "/usr/bin/env cmake"
            stdout, success = build.make_run()

        self.assertTrue(success)
        self.assertIn("Build successful", stdout)

    @patch('os.name', return_value='posix')  # Mocking Linux/Mac environment
    @patch('subprocess.run')
    def test_make_run_non_windows_failure(self, mock_subprocess):
        """ Test failed build on a non-Windows system (Linux/Mac) """
        # Mocking failed subprocess run for building
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Build failed"

        build = Build()
        build.cmd = "/usr/bin/env cmake"
        stdout, success = build.make_run()

        self.assertFalse(success)
        self.assertIn("Build failed", stdout)
