import config
from core.shell import Shell
from core.build import Build
from core.file_processor import FileProcessor
from tools import util

from sympy import primerange
from dateutil import parser

import sys
import re


class Grader:
    def __init__(self, shell, milestone):
        self.shell = shell
        self._milestone = milestone

        self._merge_config()
        self._init()

        self.score = {
            "func" : 0,
            "comments" : 0,
            "class" : 0,
        }

    def _init(self):
        self.files = self._get_files()
        if not util.check_files(self.files):
            print(f"Grader was unable to find files: {self.files}. Exiting...")
            sys.exit(1)

    def _merge_config(self):
        config.merge(f"_{self._milestone}")
        strlst = config.methods_to_strlst()
        self.clazz = config._config["class"]

        self._func_hpp = { f"{e}(" : False for e in strlst }
        self._func_hpp[f"class {self.clazz} {{"] = False
        self._func_comments = self._func_hpp.copy()

        self._func_cpp = {
            k.split(' ', 1)[0] + f" {self.clazz}::{k.split(' ', 1)[1]}" : v
            for k, v in self._func_hpp.items()
        }

    def _get_files(self):
        files = {
            "hpp" : [],
            "cpp" : []
        }

        words = util.split_clazz_name(self.clazz)
        args = ' '.join(words)

        # Run the shell scripts to find `.hpp` and `.cpp` files.
        for ext in ["hpp", "cpp"]:
            stdout, stderr, code = self.shell.cmd(f"./scripts/find_{ext}.sh {args}")
            if stdout.strip():  # Only add if there are results.
                files[ext] = stdout.strip().splitlines()

        return files


    """Check for the presence of functions in the class header and definition files."""
    def check_func(self):
        # Check the `.hpp` file for function declarations and method headers.
        processor = FileProcessor(self.files["hpp"], 'r')
        for fh in processor:
            lines = fh.readlines()
            #print(lines)
            for idx, line in enumerate(lines):
                #print(line)
                for fn, visited in self._func_hpp.items():
                    if visited:
                        continue
                    if fn in line:
                        self._func_hpp[fn] = True
                        if "*/" in lines[idx - 1] or "//" in lines[idx - 1]:
                            self._func_comments[fn] = True

        # Check the `.cpp` file for function definitions.
        processor = FileProcessor(self.files["cpp"], 'r')
        for fh in processor:
            buf = fh.read()
            #print(buf)
            for fn, visited in self._func_cpp.items():
                if visited:
                    continue
                if fn in buf:
                    self._func_cpp[fn] = True

    def count_func(self):
        func_hpp = func_cpp = func_comments = 0
        for k, v in self._func_hpp.items():
            if v:
                func_hpp += 1
        for k, v in self._func_cpp.items():
            if v:
                func_cpp += 1
        for k, v in self._func_comments.items():
            if v:
                func_comments += 1
        return func_hpp, func_cpp, func_comments
    
    def score_func(self):
        func_hpp, func_cpp, func_comments = (

            self._func_hpp, self._func_cpp, self._func_comments
        )

        # Calculate the total score from functions that are there and their
        # method headers.
        func_score = 1
        comments_score = 1
        clazz_comment = 0

        if func_hpp[f"class {self.clazz} {{"]:
            clazz_comment = 1

        func_hpp.pop(f"class {self.clazz} {{")
        func_frac = len(self._func_hpp) * 2

        for k, v in func_hpp.items():
            if not v:
                func_score -= (1 / func_frac)
        for k, v in func_cpp.items():
            if not v:
                func_score -= (1 / func_frac)
        for k, v in func_comments.items():
            if not v:
                comments_score -= (1 / len(self._func_comments))

        return func_score, comments_score, clazz_comment

    # CREDIT: OpenAI's ChatGPT
    def _check_header_dates(self, header):
        """
        This function extracts and parses date-like strings from the header.
        It returns a list of successfully parsed dates.
        """
        # Regex to match potential date formats in the header
        date_pattern = r"\b[\d/.-]+\b"
        date_strings = [match.group() for match in re.finditer(date_pattern, header)]

        parsed_dates = []
        for date_string in date_strings:
            try:
                parsed_date = parser.parse(date_string)  # Try to parse the date
                parsed_dates.append(parsed_date)  # Append the valid parsed date
            except ValueError:
                # If parsing fails, skip the invalid date
                continue
        return parsed_dates  # Return the list of valid dates    


    def check_headers(self):
        date_pattern = r"\d{2}/\d{2}/\d{2}"
        # Pattern for "Created by" or "Modified by" followed by a name
        name_pattern = r"(Created by|Modified by)\s+[\w\s]+"
    
        headers = { "hpp" : True, "cpp" : True }

        # Flatten dictionary and just send all files to FileProcessor; it will
        # determine file type.
        files = list(self.files.values())
        processor = FileProcessor(files, 'r')
        for fh in processor:
            lines = fh.readlines()
            # If file doesn't contain beginning comment block, it doesn't have
            # a header.
            if "/**" not in lines[0]:
                headers[fh.get_type()] = False
                continue
            
            # Find the end of the comment block.
            end = "".join(lines).find("*/")
            if end == -1:
                # Malformed comment block.
                headers[fh.get_type()] = False
                continue
            
            # Extract the header content.
            header = "".join(lines[:end]).strip()
            
            # Check if the file name is in the header.
            print(f"Looking for {fh.name} in header.")  # debug
            if fh.name() not in header:
                headers[fh.get_type()] = False
                continue
            
            # Check if header contains valid dates.
            if not self._check_header_dates(header):
                headers[fh.get_type()] = False
                continue
            
            # Check if the header contains the "Created by" or "Modified by" string.
            if not re.search(name_pattern, header):
                headers[fh.get_type()] = False
                continue

        score = 1
        for k, v in headers.items():
            if not v:
                score -= (1 / len(headers))
        return score


    def check_list(self):
        pts = 1
    
        found_lst = True
        lst_names = {
            "list",
            "SLL",
            "DLL",
            "SinglyLinkedList",
            "DoublyLinkedList"
        }

        # Flatten dictionary and just send all files to FileProcessor; it will
        # determine file type.
        files = list(self.files.values())
        processor = FileProcessor(files, 'r')
        for fh in processor: 
            found = False
            buf = fh.read()
            # Check if any list-related name exists in the buffer.
            if any(name in buf for name in lst_names):
                found = True
                break

            if not found:
                found_lst = False

        return pts if found_lst else 0

    def check_for(self, lst, total_points = 1, deduction = 1):
        out = []
        s = lst_to_str(lst)

        files = list(self.files.values())
        processor = FileProcessor(files, 'r')
        for fh in processor: 
            l = self.shell.cmd(f"scripts/check-for.sh ${fh} ${s}").splitlines()
            out.extend(l)

        for i in range(0, len(out)):
            # Deduct the deduction amount from total points for each found 
            # instance of "check_for".
            total_points -= deduction
            if (total_points <= 0): # points shouldn't be below zero
                total_points = 0
                break

        return total_points, out

    def check_prime(self):
        pts = 1
    
        limit = 10000
        primes = list(primerange(2, limit + 1))

        processor = FileProcessor(self.files["hpp"], 'r')
        for fh in processor:
            buf = fh.read()
            # Check if any prime number is in the file.
            if any(str(prime) in buf for prime in primes):
                return pts

        return 0

    def check_ec(self, args, points):
        ec_args = ' '.join(ec_args_lst)  # Join the list into a single string
        out = []

        files = list(self.files.values())
        processor = FileProcessor(files, 'r')
        for fh in processor:
            # xxx change script to take file as first parameter.
            stdout, stderr, code = shell.cmd(f"./check-ec.sh {ec_args}")
            out.append(stdout)

        # Calculate the total extra credit points from occurrences of extra
        # credit and points for each extra credit.
        total = 0
        for i in range(0, len(out)):
            total += points

        return total, out

    def store_impl(self):
        return 0

