from sympy import use
from sympy.logic.boolalg import Exclusive
import config
from tools import util

from core.shell import Shell
from core.build import Build
from core.grader import Grader

import os
import re

class Reporter2:
    def __init__(self, milestone, config):
        self._milestone = milestone
        self._config = config
        self._rep = {}
        self._shell = Shell()
        self._set_config()
        print("Reporter: Entered Reporter.")

    def _set_config(self):
        self._fmilestone = util.fmt_milestone(self._milestone)
        print(f"Reporter: _set_config: milestone: {self._milestone}")
        print(f"Reporter: _set_config: formatted milestone: {self._fmilestone}")

        prof = self._config['prof']
        print(f"Reporter: _set_config: professor: {prof}")
        self._repo_root = f"repos/{self._milestone}-{prof}/"
        print(f"Reporter: _set_config: repository root: {self._repo_root}")

        # Preprocess: Put our projects in a data structure to iterate.
        # xxx could also be set up ahead of time by fetch.
        self.repos = []
        print("Reporter: _set_config: Building repository list...")
        for dir in os.listdir(self._repo_root):
            print(f"Reporter: _set_config: Appended repository: {dir}.")
            self.repos.append(dir)
    
    def _get_git_username(self, repo):
        username = "XXX"
        glob = self._config['glob']

        # xxx could prolly anchor `^`, but we know this pattern works. 
        reg = re.search(f"{self._fmilestone}-{glob}-(.*)$", repo)
        if reg != None and reg[1] != None:
            username = reg[1]

        print(f"Reporter: _get_git_username: {username}.")
        return username

    def get_repos(self):
        return self.repos


    def get_git_log(self, dir):
        # Easiest way to do this is just `ls` the repo_root.
        return ""

    # xxx going to inline just milestone2, but this should be refactored into
    # config, and per milestone.
    def _fmt_build_out(self, out):
        excl_patterns = [
            r"^add key:\s*\d+$",
            r"^remove key:\s*\d+$",
            r"^getNumberOfItems:\s*\d+$",
            r"^contains\(\d+\):\s*\d+$",
            r"^isEmpty:\s*\d+$",
        ]

        lines = out.split("\n")

        # Filter out exclusion patterns.
        filtered = filter(lambda line: (
            not any(re.match(pattern, line) for pattern in excl_patterns)
        ), lines)
        lines = list(filtered)

        # Filter out blank entries (blank lines).
        filtered = filter(lambda line: (
            line.strip() != ""
        ), lines)
        lines = list(filtered)

        print(f"Grader: _fmt_build_out: {lines}")
        return lines

    def check_build_out(self, lines):
        # First, ignore every line that doesn't have the word "key" in it.
        if self._config['prof'] == 'joe':
            keylines = []
            for line in lines:
                if re.search(r'^Fifo info.*$', line, re.IGNORECASE):
                    keylines.append(line)

        else:
            keylines = []
            for line in lines:
                if "key" in line:
                    keylines.append(line)

        if self._config['prof'] == 'joe':
            match_lines = [
               # testcase1
                ["key", "50", "Name", "John Doe5", "Address", "1234 State St"],
                ["key", "40", "Name", "John Doe4", "Address", "1234 Home St"],

                # testcase2,
                [ "key", "902", "Name", "Mary Smith", "Address", "12345 Main St"],
                [ "key", "101", "Name" "John Smith", "Address", "123 Main St"],
                [ "key", "102", "Name" "John Doe1", "Address", "1234 Main St"],
                [ "key", "808", "Name", "John Doe8", "Address", "1234 Cabin St"],
                [ "key", "402", "Name" "John Doe4", "Address", "1234 Brown St"],
                [ "key", "303", "Name" "John Doe3", "Address", "1234 Elm St"],
                [ "key", "502", "Name" "John Doe5", "Address", "1234 Jack St"],
                [ "key", "602", "Name" "John Doe6", "Address", "1234 Flower St"],

                # testcase3,
                ["key", "110", "Name", "Bill Doe5", "Address", "1234 Brown St",],
                ["key", "111", "Name", "Tony Do6e", "Address", "1234 Jack St",],
                ["key", "113", "Name", "Tony Doe8", "Address", "1234 Auto St",],
                ["key", "114", "Name", "Tony Doe9", "Address", "1234 Cabin St",],
                ["key", "510", "Name",  "Bill Do2e", "Address", "1234 Main St",],
                ["key", "115", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "611", "Name", "Bill Doe4", "Address" "1234 Elm St",],
                ["key", "108", "Name", "Bill Doe3", "Address", "1234 Oak St",],

                # testcase4,
                ["key", "154", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "143", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "132", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "110", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "121", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "99", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "88", "Name", "Tony Doe8", "Address", "1234 Auto St"],
                ["key", "66", "Name", "Tony Do6e", "Address", "1234 Jack St"],
                ["key", "55", "Name", "Bill Doe5", "Address", "1234 Brown St"],
                ["key", "33", "Name", "Bill Doe3", "Address", "1234 Oak St"],
                ["key", "22", "Name", "Bill Doe5", "Address", "1234 Brown St"],
                ["key", "11", "Name", "Bill Doe3", "Address", "1234 Oak St"],

                # testcase5,
                ["key", "34", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "67", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "23", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "80", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "9", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "86", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "53", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "42", "Name", "Tony Smith10", "Address", "12345 Main St"],
            ]
        else:
            match_lines = [
                # testcase1
                ["key", "50", "Name", "John Doe5", "Address", "1234 State St"],
                ["key", "40", "Name", "John Doe4", "Address", "1234 Home St"],

                ["key", "40", "Name", "John Doe4", "Address", "1234 Home St"],
                ["key", "50", "Name", "John Doe5", "Address", "1234 State St"],

                # testcase2,
                [ "key", "902", "Name", "Mary Smith", "Address", "12345 Main St"],
                [ "key", "808", "Name", "John Doe8", "Address", "1234 Cabin St"],
                [ "key", "602", "Name" "John Doe6", "Address", "1234 Flower St"],
                [ "key", "502", "Name" "John Doe5", "Address", "1234 Jack St"],
                [ "key", "402", "Name" "John Doe4", "Address", "1234 Brown St"],
                [ "key", "303", "Name" "John Doe3", "Address", "1234 Elm St"],
                [ "key", "102", "Name" "John Doe1", "Address", "1234 Main St"],
                [ "key", "101", "Name" "John Smith", "Address", "123 Main St"],

                [ "key", "101", "Name", "John Smith", "Address", "123 Main St"],
                [ "key", "102", "Name", "John Doe1", "Address", "1234 Main St"],
                [ "key", "303", "Name", "John Doe3", "Address", "1234 Elm St"],
                [ "key", "402", "Name", "John Doe4", "Address", "1234 Brown St"],
                [ "key", "502", "Name", "John Doe5", "Address", "1234 Jack St"],
                [ "key", "602", "Name", "John Doe6", "Address", "1234 Flower St"],
                [ "key", "808", "Name", "John Doe8", "Address", "1234 Cabin St"],
                [ "key", "902", "Name", "Mary Smith", "Address", "12345 Main St"],

                # testcase3,
                ["key", "115", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "114", "Name", "Tony Doe9", "Address", "1234 Cabin St",],
                ["key", "113", "Name", "Tony Doe8", "Address", "1234 Auto St",],
                ["key", "111", "Name", "Tony Do6e", "Address", "1234 Jack St",],
                ["key", "110", "Name", "Bill Doe5", "Address", "1234 Brown St",],
                ["key", "510", "Name",  "Bill Do2e", "Address", "1234 Main St",],
                ["key", "611", "Name", "Bill Doe4", "Address" "1234 Elm St",],
                ["key", "108", "Name", "Bill Doe3", "Address", "1234 Oak St",],

                ["key", "108", "Name", "Bill Doe3", "Address", "1234 Oak St"],
                ["key", "611", "Name", "Bill Doe4", "Address", "1234 Elm St"],
                ["key", "510", "Name", "Bill Do2e", "Address", "1234 Main St"],
                ["key", "110", "Name", "Bill Doe5", "Address", "1234 Brown St"],
                ["key", "111", "Name", "Tony Do6e", "Address", "1234 Jack St"],
                ["key", "113", "Name", "Tony Doe8", "Address", "1234 Auto St"],
                ["key", "114", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "115", "Name", "Tony Smith10", "Address", "12345 Main St"],

                # testcase4,
                ["key", "154", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "143", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "132", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "110", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "121", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "99", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "88", "Name", "Tony Doe8", "Address", "1234 Auto St"],
                ["key", "66", "Name", "Tony Do6e", "Address", "1234 Jack St"],
                ["key", "55", "Name", "Bill Doe5", "Address", "1234 Brown St"],
                ["key", "33", "Name", "Bill Doe3", "Address", "1234 Oak St"],

                ["key", "33", "Name", "Bill Doe3", "Address", "1234 Oak St"],
                ["key", "55", "Name", "Bill Doe5", "Address", "1234 Brown St"],
                ["key", "66", "Name", "Tony Do6e", "Address", "1234 Jack St"],
                ["key", "88", "Name", "Tony Doe8", "Address", "1234 Auto St"],
                ["key", "99", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "121", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "110", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "132", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "143", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "154", "Name", "Tony Smith10", "Address", "12345 Main St"],

                # testcase5,
                ["key", "154", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "143", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "132", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "110", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "121", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "99", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "88", "Name", "Tony Doe8", "Address", "1234 Auto St"],
                ["key", "66", "Name", "Tony Do6e", "Address", "1234 Jack St"],
                ["key", "55", "Name", "Bill Doe5", "Address", "1234 Brown St"],
                ["key", "33", "Name", "Bill Doe3", "Address", "1234 Oak St"],

                ["key", "33", "Name", "Bill Doe3", "Address", "1234 Oak St"],
                ["key", "55", "Name", "Bill Doe5", "Address", "1234 Brown St"],
                ["key", "66", "Name", "Tony Do6e", "Address", "1234 Jack St"],
                ["key", "88", "Name", "Tony Doe8", "Address", "1234 Auto St"],
                ["key", "99", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "121", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "110", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "132", "Name", "Tony Smith10", "Address", "12345 Main St"],
                ["key", "143", "Name", "Tony Doe9", "Address", "1234 Cabin St"],
                ["key", "154", "Name", "Tony Smith10", "Address", "12345 Main St"],
            ]

        keylen = len(keylines)
        match_len = len(match_lines)
        mylen = 0
        if keylen < match_len:
            mylen = keylen
        else:
            mylen = match_len

        orig_keylines = keylines

        match = []
        for i in range(0, mylen):
            if all(e in keylines[i] for e in match_lines[i]):
                match_lines[i].insert(0, f"actual: {keylines[i]}")
                match_lines[i].insert(0, "full")
                match.append(match_lines[i])
                keylines[i] = None
            elif all(e in keylines[i] for e in match_lines[i][0:2]):
                match_lines[i].insert(0, f"actual: {keylines[i]}")
                match_lines[i].insert(0, "partial")
                match.append(match_lines[i])
                keylines[i] = None

        no_match = [line for line in keylines if line is not None]
        manifest = match

        if self._config['prof'] == 'joe':
            return manifest, orig_keylines
        else:
            return no_match, manifest

    def check_build_out_m2(self, lines):
        #testcases = [
        ##testcase1 = [
        #    ["Index", 6, [50]],
        #    ["Index", 7, [40]],
        ##]
        ##testcase2 = [
        #    ["Index", 1, [23, 67, 34]],
        #    ["Index", 3, [80]],
        #    ["Index", 9, [42, 53, 86, 9]],
        ##]
        ##testcase3 = [
        #    ["Index", 0, [110]],
        #    ["Index", 1, [111]],
        #    ["Index", 3, [113]],
        #    ["Index", 4, [510, 114]],
        #    ["Index", 5, [115]],
        #    ["Index", 6, [611]],
        #    ["Index", 9, [108]],
        ##]
        ##testcase4 = [
        #    ["Index", 1, [408]],
        #    ["Index", 2, [706]],
        #    ["Index", 3, [102]],
        #    ["Index", 4, [103]],
        #    ["Index", 5, [104, 302]],
        #    ["Index", 6, [105]],
        #    ["IndeX", 7, [403]],
        #    ["Index", 8, [206]],
        #    ["Index", 9, [504]],
        ##]
        ##testcase5 = [
        #    ["Index", 0, [902]],
        #    ["Index", 3, [102]],
        #    ["Index", 4, [103, 202]],
        #    ["Index", 5, [104, 302, 808]],
        #    ["Index", 6, [105]],
        #    ["Index", 7, [403]],
        #    ["Index", 10, [307]],
        #]

        if self._config['prof'] == "hugh":
            testcases = [
                ["testCase1:", "Index:", 6, [50]],
                ["testCase1:", "Index:", 7, [40]],
            #testcase2
                ["testCase2:", "Index:", 1, [34, 67, 23]],
                ["testCase2:", "Index:", 3, [80]],
                ["testCase2:", "Index:", 9, [9, 86, 53, 42]],
            #testcase3
                ["testCase3:", "Index:", 0, [110]],
                ["testCase3:", "Index:", 1, [111]],
                ["testCase3:", "Index:", 3, [113]],
                ["testCase3:", "Index:", 4, [114, 510]],
                ["testCase3:", "Index:", 5, [115]],
                ["testCase3:", "Index:", 6, [611]],
                ["testCase3:", "Index:", 9, [108]],
            #testcase4
                ["testCase4:", "Index:", 1, [408]],
                ["testCase4:", "Index:", 2, [706]],
                ["testCase4:", "Index:", 3, [102]],
                ["testCase4:", "Index:", 4, [103]],
                ["testCase4:", "Index:", 5, [302, 104]],
                ["testCase4:", "Index:", 6, [105]],
                ["testCase4:", "Index:", 7, [403]],
                ["testCase4:", "Index:", 8, [206]],
                ["testCase4:", "Index:", 9, [504]],
            #testcase5
                ["testCase5:", "Index:", 0, [902]],
                ["testCase5:", "Index:", 3, [102]],
                ["testCase5:", "Index:", 4, [202, 103]],
                ["testCase5:", "Index:", 5, [808, 302, 104]],
                ["testCase5:", "Index:", 6, [105]],
                ["testCase5:", "Index:", 7, [403]],
                ["testCase5:", "Index:", 10, [307]],
            ]
        elif self._config['prof'] == 'joe':
            testcases = [
            #testcase1
                ["testCase1:", "Index:", 40, [40]],
                ["testCase1:", "Index:", 50, [50]],
            #testcase2
                ["testCase2:", "Index:", 0, [101, 303, 808]],
                ["testCase2:", "Index:", 97, [602]],
                ["testCase2:", "Index:", 98, [502]],
                ["testCase2:", "Index:", 99, [402]],
            #testcase3
                ["testCase3:", "Index:", 5, [510, 611]],
                ["testCase3:", "Index:", 7, [108]],
                ["testCase3:", "Index:", 9, [110]],
                ["testCase3:", "Index:", 10, [111]],
                ["testCase3:", "Index:", 12, [113]],
                ["testCase3:", "Index:", 13, [114]],
                ["testCase3:", "Index:", 14, [115]],
            #testcase4
                ["testCase4:", "Index:", 1, [102]],
                ["testCase4:", "Index:", 2, [103]],
                ["testCase4:", "Index:", 3, [104]],
                ["testCase4:", "Index:", 4, [105, 408, 206]],
                ["testCase4:", "Index:", 100, [302, 403, 504, 706]],
            #testcase5
                ["testCase5:", "Index:", 0, [202, 808]],
                ["testCase5:", "Index:", 1, [102]],
                ["testCase5:", "Index:", 3, [104]],
                ["testCase5:", "Index:", 4, [105, 307]],
                ["testCase5:", "Index:", 94, [902]],
                ["testCase5:", "Index:", 100, [302, 403]],
            ]
        
        pattern = r"Index:\s*(\d+):\s*(.*)"

        res = []
        for line in lines:
            match = re.match(pattern, line.strip())
            if match:
                idx = int(match.group(1))
                nums = [
                    int(num) for num in re.findall(r"\d+", match.group(2))
                ]
                res.append([idx, nums])

        # Now fuzzy compare if result and testcases are equal.
        no_match = []
        manifest = []
        for case in testcases:
            testcase, index, idx, nums = case
            
            found = False
            for r in res:
                ridx, rnums = r
                if idx == ridx and (nums == rnums or nums == rnums[::-1]):
                    manifest.append(case)
                    print(f"Reporter: check_build_out: Found match: {case}")
                    found = True
                    break

            if not found:
                no_match.append(case)

        return no_match, manifest

        
    # This a very monolithic function that does almost all of the brunt of the
    # work. Private `_report()` to generate the report as a data structure. The
    # public `report()` will print the data structure to an output file.
    def _report(self):
        # We're going to set up our dictionary. Invalid git usernames are
        # indexed as f"XXX{idx++}".
        idx = 0
        incr = False
        for repo in self.repos:
            if repo == '/report':
                print('Reporter2: _report: Skipped `report` directory.')
                continue

            print(f"Reporting {repo}...")

            # Construct path.
            path = f"{self._repo_root}{repo}"
            print(f"Path: {path}")

            username = self._get_git_username(repo)
            # xxx could have better control flow
            if username == "XXX":
                username = f'XXX{idx}'
                self._rep[username] = {}
                print(f"Added to report dictionary: XXX{idx}")
                incr = True
            else:
                self._rep[username] = {}
                print(f"Added to report dictionary: {username}")

            # xxx not sure how much `subprocess.run()` retains state, so we'll
            # `cd` into the directory and `cd -` over and over again for each
            # task.
            cmd = (
                f'cd {path} && ' +
                r'echo $(git log -n 1 --pretty=format:"%h %an %ad %s") && ' +
                f'cd -'
            )
            stdout, stderr, code = self._shell.cmd(cmd)
            self._rep[username]['time'] = stdout
            print(f"git log: {stdout}")

            build = Build(self._milestone, self._config, path)

            stdout, stderr, code = self._shell.cmd(
                    f"cd {path} && ls && cd -"
            )
            print(f"ls before copy_fhs: {stdout}")

            build.copy_fhs()

            stdout, stderr, code = self._shell.cmd(
                    f"cd {path} && ls && cd -"
            )
            print(f"ls after copy_fhs: {stdout}")

            out, res = build.make_run()
            self._rep[username]['build'] = {}
            if not res:
                self._rep[username]['build']['prefmt'] = "XXX"
            else: 
                self._rep[username]['build']['prefmt'] = out
            build = None    # flag for GC
            #print(f"make_run: {out}")

            build_out = self._fmt_build_out(out)
            self._rep[username]['build']['postfmt'] = build_out
            for line in build_out:
                print(f"Reporter: build_out line: {line}")

            no_match, manifest = self.check_build_out(build_out)
            self._rep[username]['build']['no_match'] = no_match
            self._rep[username]['build']['manifest'] = manifest
            print(f"Reported: no_match list: {no_match}")
            for no in no_match:
                print(f"Reporter: no_match: {no}")

            grader = Grader(self._milestone, self._config, path)

            if self._config["extra_credit"]["enabled"]:
                print(
                    f"Reporter: extra_credit args: " +
                    f"{self._config['extra_credit']['args']}"
                )
                pts, out = grader.check_ec(
                    self._config["extra_credit"]["args"],
                    0   # xxx actually set up config for total points
                )
                
                self._rep[username]['extra_credit'] = {}
                self._rep[username]['extra_credit']['points'] = pts
                self._rep[username]['extra_credit']['output'] = out

                print(f"check_ec: {out}")

            pts, out = grader.check_headers(
                self._config["grading"]["headers"]
            )
            self._rep[username]['headers'] = {}
            self._rep[username]['headers']['points'] = pts
            self._rep[username]['headers']['output'] = out
            print(f"Reporter: check_headers: Start.")
            for line in out:
                print(f"Reporter: check_headers line: {line}")
            print(f"check_headers: End.")

            # xxx fix this nasty return with a better data structure
            pts, func_strlst, func_cpp, func_hpp, cpp_comments, hpp_comments = \
                grader.check_func(
                    self._config["grading"]["methods"]
                )
            self._rep[username]['methods'] = {}
            self._rep[username]['methods']['points'] = pts
            self._rep[username]['methods']['func_strlst'] = func_strlst
            self._rep[username]['methods']['func_cpp'] = func_cpp
            self._rep[username]['methods']['func_hpp'] = func_hpp
            self._rep[username]['methods']['cpp_comments'] = cpp_comments
            self._rep[username]['methods']['hpp_comments'] = hpp_comments
            print(f"check_func: {out}")

            grader = None   # flag for GC

            if incr:
                idx += 1
                incr = False

            # xxx check build output

    # Generates a pretty formatted report.
    def report(self):
        for k, v in self._rep.items():
            # xxx make sure reports exists.
            path = f'repos/{self._milestone}/reports/{k}_report.txt'
            out = open(path, 'w')

            out.write(util.fmtout("GitHub Username"))
            out.write("\n\n")
            out.write(k + '\n')
            out.write("\n")

            out.write(util.fmtout("Timestamp"))
            out.write("\n\n")
            out.write(v['time'] + '\n')

            # xxx headers are backwards (`.hpp`) first. maybe design API better
            # so they're better organized.
            out.write(util.fmtout("File Headers"))
            out.write("\n\n")
            lines = v['headers']['output']
            for line in lines:
                out.write(line)
                if '*/' in line or '' in line:
                    out.write('\n')
            out.write('\n') # xxx maybe not needed because of above condition

            # Unpack method information for output report.
            pts = v['methods']['points']
            func_strlst = v['methods']['func_strlst']
            func_cpp = v['methods']['func_cpp']
            func_hpp = v['methods']['func_hpp']
            cpp_comments = v['methods']['cpp_comments']
            hpp_comments = v['methods']['hpp_comments']

            out.write(util.fmtout('Methods'))
            out.write('\n\n')

            # func_strlst has an extra newline appended to it.
            out.write(func_strlst) 
            out.write('\n')

            out.write(util.fmtout('`.cpp` Method Headers'))
            out.write('\n\n')
            for e in cpp_comments.items():
                if not e[1]:
                    out.write(
                        f"MISSING method header for {e[0]}.\n"
                    )
                else:
                    out.write(
                        f"FOUND method header for {e[0]}.\n"
                    )
            out.write('\n')

            # Is just noise because we're providing header files, so impossible
            # condition guarded, but left it.
            header_comments = False
            if header_comments:
                out.write(util.fmtout('`.hpp` Method Headers'))
                for e in hpp_comments.items():
                    if not e[1]:
                        out.write(
                            f"MISSING method header for {e[0]}.\n"
                        )
                    else:
                        out.write(
                            f"FOUND method header for {e[0]}.\n"
                        )
                out.write('\n')

            out.write(util.fmtout('GTest Check'))
            out.write('\n\n')
            out.write(f'Output: {v['extra_credit']['output']}.\n')
            out.write('\n')

            out.write(util.fmtout('Output Check'))
            out.write('\n\n')

            no_match = v['build']['no_match']
            manifest = v['build']['manifest']

            out.write(f'Output:\n')
            for e in no_match:
                out.write(f'MISSING: {e}\n')
            out.write('\n')

            out.write(f'Manifest:\n')
            for e in manifest:
                out.write(f'FOUND: {e}\n')
            out.write('\n')

            out.write(util.fmtout('Build Output'))
            out.write('\n\n')

            postfmt = v['build']['postfmt']
            for line in postfmt:
                out.write(line + '\n')
            out.write('\n')

            out.write(util.fmtout('Raw Build Output'))
            out.write('\n\n')
            prefmt = v['build']['prefmt']
            out.write(prefmt)


    # xxx depricated
    def depr_report(self): 
            # pwd and regex capture project root
            self.report["name"] = self._grader.get_name()
            self.report["points"]["total"] = self._config["grading"]["total"]
    
            if self._config["options"]["build"]:
                build = Build()
                out, res = build.make_run()
    
                if not res:
                    self.report["build"] = {
                        "result" : "Build unsuccessful.",
                        "score" : 0,
                        "output" : out
                    }
                else:
                    self.report["build"] = {
                        "result" : "Build successful.",
                        "score" : self._config["grading"]["build"],
                        "output" : out
                    }
    
            if self._config["extra_credit"]["enabled"]:
                pts, out = self._grader.check_ec(self._config["extra_credit"]["args"])
                self.report["score"] = {
                    "score" : self._config["grading"]["extra_credit"],
                    "output" :  out
                }
    
            pts, out = self._grader.check_headers(self._config["grading"]["headers"])
            self.report["headers"] = {
                "score" : pts,
                "output" : out
            }
    
            # Comments for File, Class and Method headers.
            # Implementations for all of the required methods.
            pts, out = self._grader.check_func(self._config["grading"]["methods"])
            self.report["methods"] = {
                "score" : pts,
                "output" : out
            }
    
            #
            # Checks for extra items that can easily be grepped for via an argument
            # list. Including:
            #   1. Hard coded values (i.e., sizes of Hashtable, arrays, or cache,
            #      etc.)
            #
            for k, v in self._config["extra"].items():
                if v["enabled"]:
                    pts, out = self._grader.check_for(v["args"],
                                                self._config["grading"][v])
                    self.report[k] = {
                        "score" : pts,
                        "output" : out
                    }
    
            # Static variables or methods.
            pts, out = self._grader.check_static(self._config["grading"]["static"])
            self.report["static"] = {
                "score" : pts,
                "output" : out
            }
    
            # Use of STL before Milestone 4 (the implementations of the Data 
            # Structures should be hand-written, not use STL).
            if self._config["options"]["stl"]:
                pts, out = self._grader.check_stl(self._config["grading"]["stl"])
                self.report["stl"] = {
                    "score" : pts,
                    "output" : out
                }
    
            # Methods without any parameters (with the exception of getters/main).
            # xxx might be harder, but probably a grep regex pattern:
    
            # Lack of header files (all code in one file).
            pts, out = self._grader.check_hpp(self._config["grading"]["hpp"])
            self.report["hpp"] = {
                "score" : pts,
                "output" : out
            }
    
            actual = 0
            for k, v in self.report.items():
                if isinstance(v, dict):
                    actual += k.get("score", 0)
            self.report["points"]["actual"] = actual
