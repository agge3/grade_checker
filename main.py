"""
Matching expected output for our supplied testcases
Run unpublished testcases with expected output (we never got around to this)

Global variables

[x] bash script (`find_hpp.sh` returns none): Lack of header files (all code in one file)
"""

import config
from tools import util

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

from core.workspace import Workspace, create_workspace as initialize_workspace

# Grade HashTable.
def grade_hash_table():
    from core.build import Build
    from core.grader import Grader
    from core.shell import Shell

    # BUG: This legacy helper is never called and uses obsolete Build/Grader
    # constructor signatures and obsolete check-method signatures.
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


def _create_workspace_parser() -> argparse.ArgumentParser:
    """Build the parser for the workspace-creation command.

    :return: Parser describing optional non-interactive defaults.
    """
    parser = argparse.ArgumentParser(
        prog="Grade Checker create-workspace",
        description="Interactively create an empty grading workspace.",
    )
    parser.add_argument(
        "--output",
        help="Workspace directory to use instead of prompting",
    )
    parser.add_argument(
        "--milestone",
        help="Milestone configuration name to use instead of prompting",
    )
    return parser


def _print_workspace_result(workspace: Workspace) -> None:
    """Print the paths created by workspace initialization.

    :param workspace: Initialized grading workspace to summarize.
    """
    print(f"Created grading workspace: {workspace.root}")
    print(f"Workspace configuration: {workspace.configuration_path}")
    if workspace.milestone:
        print(f"Milestone: {workspace.milestone}")


def _interactive_workspace_path(workspace_name: str) -> Path:
    """Build a safe workspace path below the application workspace collection.

    :param workspace_name: User-provided name for the new grading workspace.
    :return: Path below ``grading-workspaces`` in the current directory.
    :raises ValueError: If the name is empty, absolute, or escapes the
        workspace collection.
    """
    name = Path(workspace_name)
    if not workspace_name or name.is_absolute() or ".." in name.parts:
        raise ValueError("Workspace name must be a relative directory name.")
    return Path.cwd() / "grading-workspaces" / name


def create_workspace(arguments: Sequence[str]) -> int:
    """Interactively initialize an empty grading workspace.

    :param arguments: Command-line arguments following ``create-workspace``.
    :return: Zero after the workspace is initialized.
    :raises FileExistsError: If the selected directory already has a workspace
        configuration.
    """
    parser = _create_workspace_parser()
    args = parser.parse_args(list(arguments))
    if args.output:
        output = Path(args.output)
    else:
        workspace_name = input("Workspace name [grading-workspace]: ").strip()
        output = _interactive_workspace_path(workspace_name or "grading-workspace")
    milestone = args.milestone or input(
        "Milestone configuration (optional): "
    ).strip() or None
    configuration_path = None
    if milestone:
        config.load_config(milestone)
        configuration_path = (
            Path(config.__file__).resolve().parent
            / "milestones"
            / f"_{milestone}.json"
        )
    workspace = initialize_workspace(
        output,
        milestone=milestone,
        configuration_path=configuration_path,
    )
    _print_workspace_result(workspace)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the grading CLI while preserving the legacy milestone commands.

    :param argv: Arguments to parse, or ``sys.argv[1:]`` when omitted.
    :return: Zero after the selected command completes.
    """
    command_arguments = list(sys.argv[1:] if argv is None else argv)
    if command_arguments and command_arguments[0] == "create-workspace":
        return create_workspace(command_arguments[1:])

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

    args = parser.parse_args(command_arguments)

    # EXPECTS: _milestoneX-hugh.json
    reg = re.search(r"^(\w+)-.*$", args.milestone)
    milestone = reg[1]  # expected output: milestoneX

    cfg = config.load_config(args.milestone)

    if args.fetch:
        from core.fetch import Fetcher

        fetcher = Fetcher(milestone, cfg)
        fetcher.fetch()

    if args.grade:
        from core.build import Build
        from core.grader import Grader
        from core.shell import Shell

        shell = Shell()
        grader = Grader(shell, milestone, cfg)

        name = ""   # pwd and regex capture project root
        score = cfg["grading"]["points"]
        # BUG: The score is initialized but never updated, displayed, returned,
        # or written to a report in this code path.
        
        if cfg["options"]["build"]:
            build = Build(milestone, cfg)
            out, res = build.make_run()
            
            if not res:
                # score -= cfg["grading"]["build"]
                print("Build unsuccessful. Report:")
                print(out)

        # BUG: All substantive grading checks below are commented out, so
        # --grade currently performs a build only.
            else:
                print("Build successful. Report:")
                print(out)

        # if cfg["extra_credit"]["enabled"]:
            # pts, out = grader.check_ec(cfg["extra_credit"]["args"])
            # score += cfg["grading"]["extra_credit"]
            # print(out)


        # pts, out = grader.check_headers(cfg["grading"]["headers"])
        # score -= pts
        # print(out)

        # pts, out = grader.check_func(cfg["grading"]["methods"])
        # score -= pts
        # print(out)

    if args.report:
        from core.reporter2 import Reporter2

        # BUG: Reporter2 currently calls Build and Grader with signatures that
        # do not match their active class definitions, so reporting cannot run.
        print("main: Entered Reporter.")
        reporter = Reporter2(milestone, cfg)
        reporter._report()
        reporter.report()
        # xxx we always build. keep track of what's already built to not build
        # again.



        
    return 0


if __name__ == "__main__":
    main()
