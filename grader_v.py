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
    # BUG: This is an obsolete alternate entry point. Several options are
    # commented out below but their attributes are still referenced later.
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
    # BUG: args.milestone may be None because -m is optional, which makes this
    # regular-expression call raise before the command can be handled.
    reg = re.search(r"^(\w+)-.*$", args.milestone)
    milestone = reg[1]  # expected output: milestoneX

    cfg = config.load_config(args.milestone)
    
    if args.command == "fetch":
      fetcher = NewFetcher(cfg)
      fetcher.fetch()
        #  Auth.Token()

    # BUG: args.fetch/grade/report do not exist because those argparse options
    # are commented out above.
    if args.fetch:
        fetcher = Fetcher(milestone, cfg)
        fetcher.fetch()

    if args.grade:
        shell = Shell()
        grader = Grader(shell, milestone, cfg)

        name = ""   # pwd and regex capture project root
        score = cfg["grading"]["total"]
        
        if cfg["options"]["build"]:
            build = Build()
            out, res = build.make_run()
            
            if not res:
                score -= cfg["grading"]["build"]
                print("Build unsuccessful. Report:")
                print(out)
            else:
                print("Build successful. Report:")
                print(out)

        if cfg["extra_credit"]["enabled"]:
            pts, out = grader.check_ec(cfg["extra_credit"]["args"])
            score += cfg["grading"]["extra_credit"]
            print(out)


        pts, out = grader.check_headers(cfg["grading"]["headers"])
        score -= pts
        print(out)

        pts, out = grader.check_func(cfg["grading"]["methods"])
        score -= pts
        print(out)

    if args.report:
        print("main: Entered Reporter.")
        reporter = Reporter2(milestone, cfg)
        reporter._report()
        reporter.report()
        # xxx we always build. keep track of what's already built to not build
        # again.




if __name__ == "__main__":
    main()
