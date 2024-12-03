class TestIsWindows(unittest.TestCase):
    @patch('os.name', return_value="nt")
    def test_is_windows_true(self, mock_os_name):
        self.assertTrue(_is_windows())
    
    @patch('os.name', return_value="posix")
    def test_is_windows_false(self, mock_os_name):
        self.assertFalse(_is_windows())

class TestCheckFiles(unittest.TestCase):
    @patch('__main__._check_file')
    def test_check_files_all_exist(self, mock_check_file):
        mock_check_file.return_value = True
        result = _check_files(["file1.txt", "file2.txt"])
        self.assertTrue(result)

    @patch('__main__._check_file')
    def test_check_files_some_dont_exist(self, mock_check_file):
        mock_check_file.side_effect = [True, False]  # First file exists, second doesn't
        result = _check_files(["file1.txt", "file2.txt"])
        self.assertFalse(result)

class TestSplitClazzName(unittest.TestCase):
    def test_split_clazz_name(self):
        self.assertEqual(_split_clazz_name("MyClassName"), ['My', 'Class', 'Name'])
        self.assertEqual(_split_clazz_name("TestCase"), ['Test', 'Case'])
        self.assertEqual(_split_clazz_name("AnotherTest"), ['Another', 'Test'])
        self.assertEqual(_split_clazz_name("simple"), ['simple'])  # No uppercase letters
