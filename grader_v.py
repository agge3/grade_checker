import config
from tools import util
from core.shell import Shell
from core.build import Build
from core.fetch import Fetcher
from core.grader import Grader
from core.reporter2 import Reporter2

from core.new_fetch import NewFetcher

import argparse
import re

def main():
    parser = argparse.ArgumentParser(
            prog = "V's Grade Checker"
    )
    parser.add_argument("command")
    # parser.add_argument("directory", help="The directory to process on.")
    parser.add_argument("-m", "--milestone",
                        help="Milestone to grade for")
    # parser.add_argument("-f", "--fetch", action="store_true",
    #                     help="Fetch GitHub(R) repos.")
    # parser.add_argument("-g", "--grade", action="store_true",
    #                     help="Grade fetched repos.")
    # parser.add_argument("-r", "--report", action="store_true",
    #                     help="Grade and report fetched repos.")

    args = parser.parse_args()
    
    # EXPECTS: _milestoneX-hugh.json
    reg = re.search(r"^(\w+)-.*$", args.milestone)
    milestone = reg[1]  # expected output: milestoneX

    config.merge(args.milestone)
    
    if args.command == "fetch":
      fetcher = NewFetcher(config._config)
      fetcher.fetch()
        #  Auth.Token()

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
