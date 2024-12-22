from core.shell import Shell
from core.build import Build
from core.file_processor import FileProcessor
from core.grader import Grader
from tools import util

import unittest
from unittest.mock import patch, mock_open, MagicMock
import sys
import subprocess
import os
import io


# Local globals:
_milestone = "milestone3"
_clazz = "HashTable"
_config_path = "milestones/_milestone3.json"
_fhs = (
    "HashTable.hpp\n"
    "HashTable.cpp\n"
)

_hpp = \
"""/**
*
* HashTable.hpp : This is the header file for HashTable.
*
* 09/23/24 - Created by ChatGPT
* 10/17/24 - Modified by jhui
* 12/07/24 - Modified by Tyler Baxter
*/

/**
* @class HashTable
* Chained HashTable.
*/
class HashTable {
public:
	/**
	 * Default constructor.
	 */
	HashTable();

	/** 
	 * Destructor.
	 */
	~HashTable();

    // Test different type of comment.
    HashNode** getTable();

	/**
	 * Inserts a key-value pair into HashTable.
	 *
	 * @param K key The key to be inserted.
	 * @param V value The value to be inserted.
	 */
	void add(int, HashNode*);	

	/**
	 * Removes the key-value pair with this key in HashTable.
	 *
	 * @param K key The key to remove.
	 */
	bool remove(int);

	/**
	 * Gets the value associated with the key.
	 *
	 * @param K key The key to get the value.
	 */
	HashNode* getItem(int) const;

	/**
	 * Checks whether HashTable contains the key.
	 *
	 * @return TRUE if the hash map contains the key; FALSE if the hash map does 
	 * not contain the key.
	 */
	bool contains(int) const;

	/**
	* Returns the size of HashTable.
	*
	* @return std::size_t The size.
	*/
	int getNumberOfItems() const;

	/**
	* Check whether HashTable is empty or not.
	*
	* @return TRUE if empty; FALSE if not empty.
	*/
	bool isEmpty() const;

	/**
	 * Clears the contents of HashTable.
	 */
	void clear();

    int getSize();  // test no comment above this one
private:
	const std::size_t TABLE_BUCKETS = 101;

	std::size_t _buckets;		
    std::list<V> *_table;
	std::size_t _size;
};
EOF"""

_cpp= \
"""/**
*
* HashTable.cpp
*
* 12/07/24 - Created by Tyler Baxter
*/

HashTable::HashTable()
{

}

// test different curly brace style
HashTable::~HashTable() {

}

HashNode** HashTable::getTable()
{

}

void HashTable::add(int, HashNode*)
{

}

bool HashTable::remove(int)
{

}

HashNode* HashTable::getItem(int key) const
{

}

bool HashTable::contains(int) const
{

}

int HashTable::getNumberOfItems() const
{

}

bool HashTable::isEmpty() const
{

}

void HashTable::clear()
{

}

int HashTable::getSize()
{

}
EOF"""


builtin_open = open  # save the unpatched version

# Control mock_open side effects to use the real `open` for specific files.
def _mock_open(*args, **kwargs):
    # Specific files to use "real" open:
    if args[0] == _config_path:
        return builtin_open(*args, **kwargs)
    elif args[0] == f"{_clazz}.hpp":
        return mock_hpp
    elif args[0] == f"{_clazz}.cpp":
        return mock_cpp

    # Mock open for all other files.
    return MagicMock(spec = io.StringIO)


class TestGrader(unittest.TestCase):
    def setUp(self):
        self.shell = MagicMock(Shell)
        self.build = MagicMock(Build)

    def test_get_files_err(self):
        self.shell.cmd.side_effect = [
            ("\n", "", 0),  # first call, for hpp
            ("\n", "", 0),  # second call, for cpp
        ]

        grader = Grader.__new__(Grader) # bypass Grader init procedures
        grader.shell = self.shell
        grader._milestone = _milestone
        grader._merge_config()

        files = grader._get_files()
        self.assertEqual(files["hpp"], [])
        self.assertEqual(files["cpp"], [])

        words = util.split_clazz_name(_clazz)
        args = ' '.join(words)
        for ext in ["hpp", "cpp"]:
            self.shell.cmd.assert_any_call(f"./scripts/find_{ext}.sh {args}")

    def test_get_files_succ(self):
        self.shell.cmd.side_effect = [
            (f"{_clazz}.hpp\n", "", 0),  # first call, for hpp
            (f"{_clazz}.cpp\n", "", 0),  # second call, for cpp
        ]

        grader = Grader.__new__(Grader) # bypass Grader init procedures
        grader.shell = self.shell
        grader._milestone = _milestone
        grader._merge_config()

        files = grader._get_files()
        self.assertEqual(files["hpp"], [f"{_clazz}.hpp"])
        self.assertEqual(files["cpp"], [f"{_clazz}.cpp"])

        words = util.split_clazz_name(_clazz)
        args = ' '.join(words)
        for ext in ["hpp", "cpp"]:
            self.shell.cmd.assert_any_call(f"./scripts/find_{ext}.sh {args}")

    @patch('sys.stdout', new_callable = io.StringIO)
    def test_grader_init_err(self, mock_stdout):
        self.shell.cmd.side_effect = [
            ("\n", "", 0),  # first call, for hpp
            ("\n", "", 0),  # second call, for cpp
        ]

        grader = Grader.__new__(Grader) # bypass Grader init procedures
        grader.shell = self.shell
        grader._milestone = _milestone
        grader._merge_config()

        with self.assertRaises(SystemExit) as cmd:
            grader._init()

            self.assertEqual(cmd.exception.code, 1)
            self.assertIn(
                f"Grader was unable to find files: {grader.files}. Exiting...",
                mock_stdout.getvalue()
            )

    @patch('tools.util.check_file', return_value = True)
    @patch('sys.exit')
    def test_grader_init_succ(self, mock_exit, mock_check_file):
        self.shell.cmd.side_effect = [
            (f"{_clazz}.hpp\n", "", 0),  # first call, for hpp
            (f"{_clazz}.cpp\n", "", 0),  # second call, for cpp
        ]

        grader = Grader.__new__(Grader) # bypass Grader init procedures
        grader.shell = self.shell
        grader._milestone = _milestone
        grader._merge_config()
        grader._init()

        mock_exit.assert_not_called()

    @patch('sys.stdout', new_callable = io.StringIO)
    def test_grader_ctor_err(self, mock_stdout):
        self.shell.cmd.side_effect = [
            ("\n", "", 0),  # first call, for hpp
            ("\n", "", 0),  # second call, for cpp
        ]
        
        with self.assertRaises(SystemExit) as cmd:
            grader = Grader(shell = self.shell, milestone = _milestone)

            self.assertEqual(cmd.exception.code, 1)
            self.assertIn(
                f"Grader was unable to find files: {grader.files}. Exiting...",
                mock_stdout.getvalue()
            )

    @patch('tools.util.check_file', return_value = True)
    @patch('sys.exit')
    def test_grader_ctor_succ(self, mock_exit, mock_check_file):
        self.shell.cmd.side_effect = [
            (f"{_clazz}.hpp\n", "", 0),  # first call, for hpp
            (f"{_clazz}.cpp\n", "", 0),  # second call, for cpp
        ]

        grader = Grader(shell = self.shell, milestone = _milestone)

        mock_exit.assert_not_called()

    @patch("core.file_processor.FileProcessor")
    @patch('tools.util.check_file', return_value = True)
    @patch("builtins.open", _mock_open)
    def test_check_prime(self, mock_check_file, mock_fproc):
        """ Test Grader's check_prime method """
        self.shell.cmd.side_effect = [
            (f"{_clazz}.hpp\n", "", 0),  # first call, for hpp
            (f"{_clazz}.cpp\n", "", 0),  # second call, for cpp
        ]

        # Mock FileProcessor to return a mocked file handle with a buffer.
        global mock_hpp
        mock_hpp = MagicMock(spec = io.StringIO) # behave like a file

        # Buffer:
        mock_hpp.read.return_value = _hpp

        mock_open.return_value = mock_hpp
        mock_fproc.return_value.__iter__.return_value = [mock_hpp]

        grader = Grader(shell = self.shell, milestone = _milestone)
        
        # The check_prime method should detect a prime number in the buffer and
        # return 1.
        prime_score = grader.check_prime()

        # Validate that the check_prime method detects primes correctly.
        self.assertEqual(prime_score, 1)

    @patch("core.file_processor.FileProcessor")
    @patch('tools.util.check_file', return_value=True)
    @patch("builtins.open", _mock_open)
    def test_check_list(self, mock_check_file, mock_fproc):
        """ Test Grader's check_prime method """
        self.shell.cmd.side_effect = [
            (f"{_clazz}.hpp\n", "", 0),  # first call, for hpp
            (f"{_clazz}.cpp\n", "", 0),  # second call, for cpp
        ]

        # Mock FileProcessor to return a mocked file handle with a buffer.
        global mock_hpp
        mock_hpp = MagicMock(spec = io.StringIO) # behave like a file

        # Buffer:
        mock_hpp.read.return_value = _hpp

        mock_open.return_value = mock_hpp
        mock_fproc.return_value.__iter__.return_value = [mock_hpp]

        grader = Grader(shell = self.shell, milestone = _milestone)
        
        # The check_prime method should detect a prime number in the buffer and
        # return 1.
        list_score = grader.check_list()

        # Validate that the check_prime method detects primes correctly.
        self.assertEqual(list_score, 1)


    @patch("core.file_processor.FileProcessor")
    @patch('tools.util.check_file', return_value=True)
    @patch("builtins.open", _mock_open)
    def test_check_headers(self, mock_check_file, mock_fproc):
        """ Test Grader's check_headers method """
        self.shell.cmd.side_effect = [
            (f"{_clazz}.hpp\n", "", 0),  # first call, for hpp
            (f"{_clazz}.cpp\n", "", 0),  # second call, for cpp
        ]

        # Mock FileProcessor to return a mocked file handle with a buffer.
        global mock_hpp, mock_cpp
        mock_hpp = MagicMock(spec=io.StringIO) # behave like a file
        mock_cpp = MagicMock(spec=io.StringIO) # behave like a file

        # Buffer:
        mock_hpp.read.return_value = _hpp
        mock_cpp.read.return_value = _cpp
        mock_hpp.readlines.return_value = _hpp.splitlines(keepends = True)
        mock_cpp.readlines.return_value = _cpp.splitlines(keepends = True)
        mock_hpp.get_type = MagicMock(return_value = ".hpp")
        mock_cpp.get_type = MagicMock(return_value = ".cpp")
        mock_hpp.name = MagicMock(return_value = "HashTable")
        mock_cpp.name = MagicMock(return_value = "HashTable")

        mock_open.side_effect = [mock_hpp, mock_cpp]
        mock_fproc.return_value.__iter__.return_value = [mock_hpp, mock_cpp]

        grader = Grader(shell = self.shell, milestone = _milestone)
        
        header_score = grader.check_headers()

        self.assertEqual(header_score, 1)

    @patch("core.file_processor.FileProcessor")
    @patch('tools.util.check_file', return_value = True)
    @patch("builtins.open", _mock_open)
    def test_check_func(self, mock_check_file, mock_fproc):
        """ Test Grader's check_func method. """
        self.shell.cmd.side_effect = [
            (f"{_clazz}.hpp\n", "", 0),  # first call, for hpp
            (f"{_clazz}.cpp\n", "", 0),  # second call, for cpp
        ]

        # Mock FileProcessor to return a mocked file handle with a buffer.
        global mock_hpp, mock_cpp
        mock_hpp = MagicMock(spec = io.StringIO) # behave like a file
        mock_cpp = MagicMock(spec = io.StringIO)

        # Buffer:
        mock_hpp.read.return_value = _hpp
        mock_cpp.read.return_value = _cpp
        mock_hpp.readlines.return_value = _hpp.splitlines(keepends = True)
        mock_cpp.readlines.return_value = _cpp.splitlines(keepends = True)

        #mock_open.side_effect = [mock_hpp, mock_cpp]
        mock_fproc.return_value.__iter__.return_value = [mock_hpp, mock_cpp]

        grader = Grader(shell = self.shell, milestone = _milestone)

        grader.check_func()
        func_hpp, func_cpp, func_comments = grader.count_func()

        # All header functions are in the buffer; this should be all.
        self.assertEqual(func_hpp, 10)

        # One implementation is missing in the buffer; this should be one less
        # than the header score.
        self.assertEqual(func_cpp, 9)

        # One comment is missing for the comments; this should be one less than
        # the header score.
        self.assertEqual(func_comments, 9)
 
    #@patch("core.file_processor.FileProcessor")
    #@patch('tools.util.check_file', return_value=True)
    #@patch("builtins.open", new_callable=MagicMock)  # Mocking open()
    #def test_check_func(self, mock_open, mock_check_file, mock_file_processor):
    #    """ Test Grader's check_func method """
    #    self.shell.cmd.side_effect = [
    #        (f"{_clazz}.hpp\n", "", 0),  # first call, for hpp
    #        (f"{_clazz}.cpp\n", "", 0),  # second call, for cpp
    #    ]

    #    # Mock FileProcessor to return dummy file handles
    #    mock_file_processor.return_value.__iter__.return_value = [
    #        MagicMock(readlines=MagicMock(return_value=["class MyClass {", "HashNode** getTable(", "*/"])),
    #        MagicMock(read=MagicMock(return_value="int getSize(int a) {"))
    #    ]

    #    # Mock the behavior of open to avoid actual file operations
    #    mock_file = MagicMock(spec=io.IOBase)
    #    mock_file.readlines.return_value = ["class MyClass {", "HashNode** getTable(", "*/"]
    #    mock_file.read.return_value = "int getSize(int a) {"
    #    mock_open.return_value = mock_file  # Return the mock file when open() is called

    #    grader = Grader(shell=self.shell, clazz=_clazz)
    #    func_score, comments_score, clazz_comment = grader.check_func()

    #    # Validate that the function checking method works and returns correct scores
    #    self.assertEqual(func_score, 1)
    #    self.assertEqual(comments_score, 1)
    #    self.assertEqual(clazz_comment, 1)

    #    # Ensure that the open function was called with the correct file path
    #    mock_open.assert_any_call(f"{_clazz}.hpp", "r")
    #    mock_open.assert_any_call(f"{_clazz}.cpp", "r")

    #@patch("core.shell.Shell.cmd")
    #@patch("core.file_processor.FileProcessor")
    #def test_check_headers(self, mock_file_processor, mock_cmd):
    #    """ Test Grader's check_headers method """

    #    # Mock shell cmd to return dummy .hpp and .cpp files
    #    mock_cmd.return_value = ("/path/to/header.hpp\n", "", 0)

    #    # Mock FileProcessor to return dummy file handles
    #    mock_file_processor.return_value.__iter__.return_value = [
    #        MagicMock(readlines=MagicMock(return_value=["/**", "Created by John Doe", "*/"])),
    #        MagicMock(readlines=MagicMock(return_value=["/**", "Modified by Jane Doe", "*/"]))
    #    ]

    #    grader = Grader(shell=MagicMock(), clazz="MyClass")
    #    score = grader.check_headers()

    #    # Validate that the header checking logic works correctly
    #    self.assertEqual(score, 1)

    #@patch("core.shell.Shell.cmd")
    #@patch("core.file_processor.FileProcessor")
    #def test_check_list(self, mock_file_processor, mock_cmd):
    #    """ Test Grader's check_list method """

    #    # Mock shell cmd to return dummy .hpp and .cpp files
    #    mock_cmd.return_value = ("/path/to/list.hpp\n", "", 0)

    #    # Mock FileProcessor to return dummy file handles
    #    mock_file_processor.return_value.__iter__.return_value = [
    #        MagicMock(read=MagicMock(return_value="SinglyLinkedList"))
    #    ]

    #    grader = Grader(shell=MagicMock(), clazz="MyClass")
    #    list_score = grader.check_list()

    #    # Validate that the check_list method detects list types correctly
    #    self.assertEqual(list_score, 1)

    #@patch("core.shell..Shell.cmd")
    #@patch("core.file_processor..FileProcessor")
    #def test_check_prime(self, mock_file_processor, mock_cmd):
    #    """ Test Grader's check_prime method """

    #    # Mock shell cmd to return dummy .hpp files
    #    mock_cmd.return_value = ("/path/to/file.hpp\n", "", 0)

    #    # Mock FileProcessor to return dummy file handles
    #    mock_file_processor.return_value.__iter__.return_value = [
    #        MagicMock(read=MagicMock(return_value="HashNode* getItem(int i) { return 3; }"))
    #    ]

    #    grader = Grader(shell=MagicMock(), clazz="MyClass")
    #    prime_score = grader.check_prime()

    #    # Validate that the check_prime method detects primes correctly
    #    self.assertEqual(prime_score, 1)

    #@patch("shell.Shell.cmd")
    #@patch("core.file_processor.FileProcessor")
    #def test_check_prime_no_prime(self, mock_file_processor, mock_cmd):
    #    """ Test Grader's check_prime method with no primes """

    #    # Mock shell cmd to return dummy .hpp files
    #    mock_cmd.return_value = ("/path/to/file.hpp\n", "", 0)

    #    # Mock FileProcessor to return dummy file handles
    #    mock_file_processor.return_value.__iter__.return_value = [
    #        MagicMock(read=MagicMock(return_value="HashNode* getItem(int i) { return 2; }"))
    #    ]

    #    grader = Grader(shell=MagicMock(), clazz="MyClass")
    #    prime_score = grader.check_prime()

    #    # Validate that the check_prime method returns 0 when no prime is found
    #    self.assertEqual(prime_score, 0)


if __name__ == "__main__":
    unittest.main()
