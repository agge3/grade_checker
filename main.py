"""
Matching expected output for our supplied testcases
Run unpublished testcases with expected output (we never got around to this)

Global variables

[x] bash script (`find_hpp.sh` returns none): Lack of header files (all code in one file)
"""

import config
from tools import util
from core.shell import Shell
from core.build import Build
from core.fetch import Fetcher
from core.grader import Grader
from core.reporter2 import Reporter2

import argparse
import re

# Grade HashTable.
def grade_hash_table():
    shell = Shell()
    build = Build()

    grader = Grader(shell, "HashTable")
    score = 0

    # Helper script to grade extra credit.
    ec_args_lst = [
        "--smart_ptrs",
        "--templates",
        "--gtest",
    ]
    # Fixing the join statement
    ec_args = ' '.join(ec_args_lst)  # Join the list into a single string

    # Run the extra credit script
    stdout, stderr, code = shell.cmd(f"./check-ec.sh {ec_args}")
    try:
        score += float(stdout)  # Add the extra credit score
    except ValueError as e:
        print(e)

    # Generic grading (applies to all milestones).
    score += grader.check_headers()
    func_score, comments_score, clazz_comment = grader.check_func()
    score += func_score + comments_score + clazz_comment  # Simplified this part

    # HashTable specific grading.
    score += grader.check_prime()
    score += grader.check_list()

    return score  # Return the final grade score


def main():
    parser = argparse.ArgumentParser(
            prog = "Grade Checker"
    )
    parser.add_argument("milestone")
    parser.add_argument("-f", "--fetch", action="store_true",
                        help="Fetch GitHub(R) repos.")
    parser.add_argument("-g", "--grade", action="store_true",
                        help="Grade fetched repos.")
    parser.add_argument("-r", "--report", action="store_true",
                        help="Grade and report fetched repos.")

    args = parser.parse_args()

    # EXPECTS: _milestoneX-hugh.json
    reg = re.search(r"^(\w+)-.*$", args.milestone)
    milestone = reg[1]  # expected output: milestoneX

    config.merge(args.milestone)

    if args.fetch:
        fetcher = Fetcher(milestone, config._config)
        fetcher.fetch()

    if args.grade:
        shell = Shell()
        grader = Grader(shell, milestone, config)

        name = ""   # pwd and regex capture project root
        score = config._config["grading"]["total"]
        
        if config._config["options"]["build"]:
            build = Build()
            out, res = build.make_run()
            
            if not res:
                score -= config._config["grading"]["build"]
                print("Build unsuccessful. Report:")
                print(out)
            else:
                print("Build successful. Report:")
                print(out)

        if config._config["extra_credit"]["enabled"]:
            pts, out = grader.check_ec(config._config["extra_credit"]["args"])
            score += config._config["grading"]["extra_credit"]
            print(out)


        pts, out = grader.check_headers(config._config["grading"]["headers"])
        score -= pts
        print(out)

        pts, out = grader.check_func(config._config["grading"]["methods"])
        score -= pts
        print(out)

    if args.report:
        print("main: Entered Reporter.")
        reporter = Reporter2(milestone, config._config)
        reporter._report()
        reporter.report()
        # xxx we always build. keep track of what's already built to not build
        # again.



        



if __name__ == "__main__":
    main()
