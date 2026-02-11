import config
from core.shell import Shell
from core.build import Build
from core.file_processor import FileProcessor
from tools import util

from sympy import primerange
from dateutil import parser

import sys
import re

class Logger:
    def __init__(self, filename="debug.log"):
        self.filename = filename

    def log(self, level, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"
        with open(self.filename, "a") as f:
            f.write(log_message)

logger = Logger()

cpp_headers = False


class Grader:
    def __init__(self, milestone, config, path=""):
        self._shell = Shell()
        self._milestone = milestone
        self._config = config
        self._path = path

        # merge_config and instantiated Grader config
        self._func_hpp = {}
        self._func_cpp = {}
        self._hpp_comments = {}
        self._cpp_comments = {}
        self._merge_config()

        # init and instantiated Grader init
        self.files = {}
        self._init()

        self.score = {
            "func" : 0,
            "comments" : 0,
            "class" : 0,
        }

    def _init(self):
        self.files = self._get_files()

        # xxx not really necessary as there will simply be no file output if
        # they don't exist!
        #if not util.check_files(self.files):
        #    # xxx log
        #    print(f"Grader was unable to find files: {self.files}. Exiting...")
        #    sys.exit(1)

    # Grader requires additional config setup from the passed config object.
    # Helper function dedicated to merging them into Grader's state.
    def _merge_config(self):
        strlst = util.methods_to_strlst(self._config)
        self.clazzes = self._config["classes"]
        for clazz in self.clazzes:
            print(f"Grader: class: {clazz}")

            self._func_hpp[clazz] = { f"{e}(" : False for e in strlst[clazz] }
            # xxx we don't need to grade class
            #self._func_hpp[f"class {self.clazz} {{"] = False
            self._hpp_comments[clazz] = self._func_hpp.copy()
            print(f"Grader: _merge_config: _hpp_comments: "
                  f"{self._hpp_comments[clazz]}.")

            self._func_cpp[clazz] = {
                k.split(' ', 1)[0] + f" {clazz}::{k.split(' ', 1)[1]}" : v
                for k, v in self._func_hpp[clazz].items()
            }
            self._cpp_comments[clazz] = self._func_cpp[clazz].copy()

    def _get_files(self):
        files = {
            "hpp" : {},
            "cpp" : {},
        }

        for clazz in self.clazzes:
            words = util.split_clazz_name(clazz)
            args = ' '.join(words)

            # Run the shell scripts to find `.hpp` and `.cpp` files.
            for ext in ["hpp", "cpp"]:
                if self._path != "":
                    # Have to backtrack a directory to be back in root from scripts.
                    cmd = f"./scripts/find-{ext}.sh {self._path} {args}"
                    print(f"Grader: find-{ext}.sh command: {cmd}")

                    stdout, stderr, code = self._shell.cmd(cmd)
                    print(f"Grader: _get_files: {stdout}")

                    if stdout.strip():  # Only add if there are results.
                        files[ext][clazz] = \
                            f"{self._path}/{stdout.strip().splitlines()[0]}"
                else:
                    # xxx handle handle path (root path).
                    print("Grader: _get_files: Empty path.")

        return files


    """Check for the presence of functions in the class header and definition files."""
    def check_func(self, points):
        func_strlst_dict = {}
        pts_dict = {}

        for clazz in self.clazzes:
            func_strlst = ""

            # xxx skipping header files, because those aren't consistently
            # graded
            # Check the `.hpp` file for function declarations and method headers.
            """
            processor = FileProcessor(self.files["hpp"][clazz], 'r')
            for fh, ftype in processor:
                lines = fh.readlines()
                #print(lines)
                for idx, line in enumerate(lines):
                    #print(line)
                    for fn, visited in self._func_hpp[clazz].items():
                        if visited:
                            continue
                        if fn in line:
                            func_strlst += f"FOUND: {fn} in {fh.name}\n"

                            self._func_hpp[clazz][fn] = True

                            inline = lambda l: (
                                re.search(r"//", l) or
                                (re.search(r"/\*", l) and re.search(r"\*/", l))
                                # xxx could capture `/* .* */`
                            )

                            if ("*/" in lines[idx - 1] or "//" in lines[idx - 1] or
                                inline(line)):
                                self._hpp_comments[clazz][fn] = True
                                print(
                                    f"Grader: check_func: FOUND method header in "
                                    f"{fh.name} for {fn}."
                                )
                                if inline(line):
                                    print(
                                        f"Grader: check_func: Method header line "
                                        f"in {fh.name} at lines[{idx}]: "
                                        f"{line.strip()}."
                                    )
                                else:
                                    print(
                                        f"Grader: check_func: Method header line "
                                        f"in {fh.name} at lines[{idx - 1}: "
                                        f"{lines[idx - 1].strip()}."
                                    )

                for e in self._func_hpp[clazz].items():
                    if not e[1]:
                        func_strlst += f"MISSING {e[0]} in {fh.name}\n"
                for e in self._hpp_comments[clazz].items():
                    if not e[1]:
                        print(
                            f"Grader: check_func: MISSING method header for {e[0]} "
                            f"in {fh.name}."
                        )
                    else:
                        print(
                            f"Grader: check_func: FOUND method header for {e[0]} "
                            f"in {fh.name}."
                        )
            """

            try:
                processor = FileProcessor(self.files["cpp"][clazz], 'r')
                for fh, ftype in processor:
                    lines = fh.readlines()
                    #print(lines)
                    for idx, line in enumerate(lines):
                        #print(line)
                        for fn, visited in self._func_cpp[clazz].items():
                            if visited:
                                continue
                            if fn in line:
                                func_strlst += f"FOUND: {fn} in {fh.name}\n"

                                self._func_cpp[clazz][fn] = True

                                inline = lambda l: (
                                    re.search(r"//", l) or
                                    (re.search(r"/\*", l) and re.search(r"\*/", l))
                                    # xxx could capture `/* .* */`
                                )

                                if ("*/" in lines[idx - 1] or "//" in lines[idx - 1] or
                                    inline(line)):
                                    self._cpp_comments[clazz][fn] = True
                                    print(
                                        f"Grader: check_func: FOUND method header in "
                                        f"{fh.name} for {fn}."
                                    )
                                    if inline(line):
                                        print(
                                            f"Grader: check_func: Method header line "
                                            f"in {fh.name} at lines[{idx}]: "
                                            f"{line.strip()}."
                                        )
                                    else:
                                        print(
                                            f"Grader: check_func: Method header line "
                                            f"in {fh.name} at lines[{idx - 1}: "
                                            f"{lines[idx - 1].strip()}."
                                        )

                    for e in self._func_cpp[clazz].items():
                        if not e[1]:
                            func_strlst += f"MISSING {e[0]} in {fh.name}\n"
                    for e in self._cpp_comments[clazz].items():
                        if not e[1]:
                            print(
                                f"Grader: check_func: MISSING method header for {e[0]} "
                                f"in {fh.name}."
                            )
                        else:
                            print(
                                f"Grader: check_func: FOUND method header for {e[0]} "
                                f"in {fh.name}."
                                )
            except KeyError as e:
                func_strlst = f"File NOT FOUND for class {clazz}: {e}"

            # Check the `.cpp` file for function definitions.
            if cpp_headers:
                try:
                    processor = FileProcessor(self.files["cpp"][clazz], 'r')
                    for fh in processor:
                        buf = fh.read()
                        #print(buf)
                        for fn, visited in self._func_cpp[clazz].items():
                            if visited:
                                continue
                            if fn in buf:
                                self._func_cpp[clazz][fn] = True
                except KeyError as e:
                    print(f"ERROR: File NOT FOUND for class {clazz}: {e}")

            func_strlst_dict[clazz] = func_strlst
            pts_dict[clazz] = 0

            #print(f"XXX Grader: func_strlst: {func_strlst}")

        # xxx actually calculate points
        # xxx fix this nasty return as a data structure
        return (
            pts_dict, func_strlst_dict, self._func_cpp, self._func_hpp,
            self._cpp_comments, self._hpp_comments
        )

    # xxx completely broken by _func_comments -> _hpp/cpp_comments change
    # xxx completely broken by _func_(hpp|cpp|comments) ->
    # _func_(hpp|cpp|comments)[clazz] change
    def count_func(self):
        func_hpp = func_cpp = func_comments = 0
        for k, v in self._func_hpp.items():
            if v:
                func_hpp += 1
        for k, v in self._func_cpp.items():
            if v:
                func_cpp += 1
        #for k, v in self._func_comments.items():
        #    if v:
        #        func_comments += 1
        return func_hpp, func_cpp, func_comments

    # xxx completely broken by _func_(hpp|cpp|comments) ->
    # _func_(hpp|cpp|comments)[clazz] change
    def get_func_comments(self):
        return self._func_comments

    # xxx completely broken by _func_(hpp|cpp|comments) ->
    # _func_(hpp|cpp|comments)[clazz] change
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


    def check_headers(self, points):
        # xxx return total points

        date_pattern = r"\d{2}/\d{2}/\d{2}"
        # Pattern for "Created by" or "Modified by" followed by a name
        name_pattern = r"(Created by|Modified by)\s+[\w\s]+"
        cap_headers = []
        output = {}
        header_cnt = 0
        header_missing = 0

        for clazz in self.clazzes:
            output[clazz] = {}
            headers = { "hpp" : True, "cpp" : True }

            # Flatten dictionary and just send all files to FileProcessor; it will
            # determine file type.
            # xxx skipping header files, because those aren't consistently
            # graded
            #files = [
            #        f
            #        for clazzes in self.files.values()
            #        for f in clazzes.values()
            #]
            try:
                processor = FileProcessor(self.files["cpp"][clazz], 'r')
                for fh, ftype in processor:
                    lines = fh.readlines()

                    if not lines:
                        print("WARNING: empty file. skipping...")
                        continue

                    #cap_headers.append(util.fmtout(f"{fh.name} HEADER"))

                    # If file doesn't contain beginning comment block, it doesn't have
                    # a header.
                    if ("/**" or "//" or "/*") not in lines[0]:
                        headers[ftype] = False
                        print(
                            f"lines[0] did not contain a comment starting block in "
                            f"{fh.name}."
                        )
                        output[clazz]['no_header'] = (
                            f"lines[0] did not contain a comment starting block in "
                            f"{fh.name}."
                        )
                        continue
                    else:
                        print(f"Found header comment starting block.")

                    # Find the end of the comment block.
                    #end = "".join(lines).find("*/") or "".join(lines).find("\n")
                    end = next(
                        (i for i, line in enumerate(lines)
                        if line.strip() == "" or "*/" in line),
                        -1
                    )
                    # Sanity check: Header shouldn't be longer than 25 lines.
                    if end > 25:
                        end -1

                    if end == -1:
                        # Malformed comment block.
                        print(
                            f"Malformed comment block in {fh.name}."
                        )
                        output[clazz]['malformed_header'] = (
                            f"Malformed comment block in {fh.name}."
                        )
                        headers[ftype] = False
                        continue
                    else:
                        print(f"Header comment block is not malformed.")
                        print(f"Header starts on lines[0] and ends on lines[{end}].")

                    # Extract the header content.
                    for i in range(0, end + 1):
                        cap_headers.append(lines[i].strip())
                        print(f"Grader: Found header line: {lines[i].strip()}.")
                    #cap_headers += "\n"

                    # xxx refactor the below to list.
                    # Check if the file name is in the header.
                    #print(f"Looking for {fh.name} in header.")  # debug
                    #if fh.name not in cap_headers:
                    #    headers[ftype] = False
                    #    continue
                    #
                    ## Check if header contains valid dates.
                    #if not self._check_header_dates(cap_headers):
                    #    headers[ftype] = False
                    #    print("Header date did not match pattern.")
                    #    continue
                    #else:
                    #    print("Found a header date that matches pattern.")
                    #
                    ## Check if the header contains the "Created by" or "Modified by" string.
                    #if not re.search(name_pattern, cap_headers):
                    #    headers[ftype] = False
                    #    print('Could not find "Created/Modified By" string in header.')
                    #    continue
                    #else:
                    #    print('Found "Created/Modified By" string in header.')
            except KeyError as e:
                cap_headers.append(f"File NOT FOUND for class: {clazz}: {e}")
                output[clazz]['no_file'] = (
                    f"File NOT FOUND for class: {clazz}: {e}"
                    )

            header_cnt = header_cnt + len(headers)
            for k, v in headers.items():
                if not v:
                    header_missing = header_missing + 1

        score = 1 * (header_missing / header_cnt)

        return score, cap_headers

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
        ec_args = ' '.join(args)  # Join the list into a single string.
        out = []

        files = list(self.files.values())
        processor = FileProcessor(files, 'r')
        for fh in processor:
            # xxx change script to take file as first parameter.
            stdout, stderr, code = self._shell.cmd(f"./check-ec.sh {ec_args}")
            out.append(stdout)

        # Calculate the total extra credit points from occurrences of extra
        # credit and points for each extra credit.
        total = 0
        for i in range(0, len(out)):
            total += points

        return total, out

    def store_impl(self):
        return 0

