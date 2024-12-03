import os
import subprocess
import shutil
import sys
from sympy import primerange
from dateutil import parser
import re


def is_windows():
    """Check if the OS is Windows."""
    return os.name == "nt"

def get_git_bash_path():
    """Find Git Bash executable on Windows."""
    possible_paths = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ]
    for path in possible_paths:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError("Git Bash not found. Please install Git Bash.")


def run_command(command, use_git_bash=False):
    """
    Run a shell command.
    On Windows, use Git Bash if specified; otherwise, run normally.
    """
    if use_git_bash and is_windows():
        git_bash_path = get_git_bash_path()
        bash_command = f'{" ".join(command)}'
        result = subprocess.run([git_bash_path, "-c", bash_command], capture_output=True, text=True)
    else:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

    return result.stdout, result.stderr, result.returncode


def check_dependencies():
    """Ensure required dependencies like `grep` are available."""
    try:
        stdout, stderr, code = run_command(["grep --version"], use_git_bash=is_windows())
        if code != 0:
            raise RuntimeError(f"grep check failed with error: {stderr}")
        print("grep is available.")
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)


def get_files():
    """Retrieve HPP and CPP files containing hash map references."""
    files = {}
    stdout, stderr, code = run_command(
        "grep -i -r -l -E 'hash[- ]?map[- ]?\.(hpp|h|hh)' *", use_git_bash=is_windows()
    )
    files["hpp"] = stdout.strip()
    stdout, stderr, code = run_command(
        "grep -i -r -l -E 'hash[- ]?map[- ]?\.(cpp|cxx|cc)' *", use_git_bash=is_windows()
    )
    files["cpp"] = stdout.strip()
    return files


def check_header_dates(header):
    """
    Extract and validate date-like strings in the header.
    Returns True if valid dates are found.
    """
    date_pattern = r"\b[\d/.-]+\b"
    date_strings = re.findall(date_pattern, header)

    for date_string in date_strings:
        try:
            parser.parse(date_string)  # Validate date format
            return True
        except ValueError:
            continue
    return False


def check_headers(files):
    """
    Verify headers in HPP and CPP files for format and content:
    - Include file name
    - Contain valid date(s)
    - Contain "Created by"/"Modified by" pattern
    """
    name_pattern = r"(Created by|Modified by)\s+[\w\s]+"
    headers = {"hpp": True, "cpp": True}

    for ftype, file_path in files.items():
        with open(file_path, 'r') as fh:
            lines = fh.readlines()
            if not lines or "/**" not in lines[0]:
                headers[ftype] = False
                continue

            end_index = next((i for i, line in enumerate(lines) if "*/" in line), -1)
            if end_index == -1:
                headers[ftype] = False
                continue

            header = "".join(lines[:end_index + 1]).strip()
            file_name = os.path.basename(file_path)
            if file_name not in header or not check_header_dates(header) or not re.search(name_pattern, header):
                headers[ftype] = False

    return sum(headers.values()) / len(headers)  # Score as fraction of valid headers


def check_func(files):
    """
    Verify function declarations and implementations in HPP and CPP files.
    """
    clazz = "HashTable"
    func_hpp = {
        f"class {clazz} {{": False,
        "HashNode** getTable(": False,
        "int getSize(": False,
        "bool isEmpty(": False,
        "int getNumberOfItems(": False,
        "bool add(": False,
        "bool remove(": False,
        "void clear(": False,
        "HashNode* getItem(": False,
        "bool contains(": False,
    }
    func_cpp = {f"{line.split(' ', 1)[0]} {clazz}::{line.split(' ', 1)[1]}": False for line in func_hpp.keys()}

    with open(files["hpp"], 'r') as fh:
        lines = fh.readlines()
        for idx, line in enumerate(lines):
            for func, visited in func_hpp.items():
                if not visited and func in line:
                    func_hpp[func] = True

    with open(files["cpp"], 'r') as fh:
        buf = fh.read()
        for func, visited in func_cpp.items():
            if not visited and func in buf:
                func_cpp[func] = True

    total_funcs = len(func_hpp) + len(func_cpp)
    implemented = sum(func_hpp.values()) + sum(func_cpp.values())
    return implemented / total_funcs


def check_list(files):
    """Check if list-related keywords are present in all files."""
    lst_names = {"list", "SLL", "DLL", "SinglyLinkedList", "DoublyLinkedList"}
    for file_path in files.values():
        with open(file_path, 'r') as fh:
            buf = fh.read()
            if not any(name in buf for name in lst_names):
                return 0
    return 1


def check_prime(files):
    """Check if any prime number under 10,000 is mentioned in the HPP file."""
    primes = set(primerange(2, 10001))
    with open(files["hpp"], 'r') as fh:
        buf = fh.read()
        for prime in primes:
            if str(prime) in buf:
                return 1
    return 0


def main():
    check_dependencies()

    files = get_files()
    score = 0

    score += check_headers(files)
    score += check_func(files)
    score += check_list(files)
    score += check_prime(files)

    print(f"Final score: {score}")


if __name__ == "__main__":
    main()

