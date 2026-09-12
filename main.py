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
from core.submission_importer import ImportResult, SubmissionImporter

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


def _import_submissions_parser() -> argparse.ArgumentParser:
    """Build the parser for importing submissions into a workspace.

    :return: Parser describing the submission-import options.
    """
    parser = argparse.ArgumentParser(
        prog="Grade Checker import-student-canvas-submissions",
        description="Import student-canvas-submissions into a grading workspace.",
    )
    parser.add_argument("--workspace", help="Initialized grading workspace directory")
    parser.add_argument(
        "--student-canvas-submissions", "--archive",
        dest="student_canvas_submissions",
        help="Student-canvas-submissions ZIP exported from Canvas",
    )
    parser.add_argument("--required-file", help="Required student filename, such as milestone1.cpp")
    parser.add_argument(
        "--optional-file",
        action="append",
        dest="optional_files",
        default=None,
        help="Optional file allowed in submitted ZIPs; may be repeated",
    )
    return parser


def _print_import_result(result: ImportResult) -> None:
    """Print a human-readable summary of an import operation.

    :param result: Import result to summarize.
    """
    print(f"Imported submissions: {len(result.submissions)}")
    if result.raw_archive:
        print(f"Student-canvas-submissions: {result.raw_archive}")
    for submission in result.submissions:
        print(f"  {submission.identifier}: {submission.workspace}")
        for warning in submission.warnings:
            print(f"    warning: {warning}")
    for warning in result.warnings:
        if not any(warning.endswith(item) for submission in result.submissions for item in submission.warnings):
            print(f"warning: {warning}")


def _existing_workspaces() -> list[Path]:
    """Find initialized workspaces in the default workspace collection.

    :return: Existing directories containing a ``workspace.json`` file.
    """
    workspace_root = Path.cwd() / "grading-workspaces"
    if not workspace_root.is_dir():
        return []
    return sorted(
        path for path in workspace_root.iterdir()
        if path.is_dir() and (path / "workspace.json").is_file()
    )


def _clean_entered_value(value: str) -> str:
    """Normalize a value pasted into a prompt or dragged from a file browser.

    :param value: Raw text entered by the user.
    :return: Trimmed text with one matching pair of surrounding quotes removed.
    """
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in "'\"":
        return cleaned[1:-1]
    return cleaned


def _custom_workspace_path() -> str:
    """Prompt for a manually supplied path with editing and completion.

    :return: The entered workspace path with surrounding whitespace removed.
    :raises EOFError: If interactive input ends before the path is entered.
    """
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return _clean_entered_value(input("Custom workspace directory: "))
    try:
        import questionary
    except ImportError:
        return input("Custom workspace directory: ").strip()

    answer = questionary.path("Workspace directory:").ask()
    if answer is None:
        raise ValueError("Workspace path prompt was cancelled.")
    return _clean_entered_value(answer)


def _select_workspace_numbered(options: list[Path | str]) -> str:
    """Select a workspace using a numbered prompt.

    :param options: Existing workspace paths followed by the custom-path option.
    :return: Selected or manually entered workspace directory.
    :raises ValueError: If the entered selection is not valid.
    """
    print("Select a workspace:")
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option}")
    selection = input("Workspace number: ").strip()
    try:
        selected_index = int(selection) - 1
    except ValueError as error:
        raise ValueError("Workspace selection must be a number.") from error
    if selected_index < 0 or selected_index >= len(options):
        raise ValueError("Workspace selection is out of range.")
    selected = options[selected_index]
    return _custom_workspace_path() if isinstance(selected, str) else str(selected)


def _select_workspace_interactively() -> str:
    """Select an existing workspace with keyboard navigation or enter a path.

    :return: Selected or manually entered workspace directory.
    :raises EOFError: If interactive input ends before a selection is made.
    """
    choices = _existing_workspaces()
    custom_label = "Enter a custom workspace path"
    options = [*choices, custom_label]
    if not options:
        return _custom_workspace_path()

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return _select_workspace_numbered(options)

    try:
        import questionary
    except ImportError:
        return _select_workspace_numbered(options)

    selected = questionary.select(
        "Select a workspace:",
        choices=[str(option) for option in choices] + [custom_label],
    ).ask()
    if selected == custom_label:
        return _custom_workspace_path()
    if selected is None:
        raise ValueError("Workspace selection was cancelled.")
    return selected


def import_submissions(arguments: Sequence[str]) -> int:
    """Import student-canvas-submissions into an initialized grading workspace.

        :param arguments: Arguments following
            ``import-student-canvas-submissions``.
    :return: Zero after a successful import.
    :raises FileNotFoundError: If the workspace or student-canvas-submissions
        file does not exist.
    :raises ValueError: If student-canvas-submissions is invalid or unsafe.
    """
    parser = _import_submissions_parser()
    args = parser.parse_args(list(arguments))
    try:
        import questionary
    except ImportError:
        questionary = None
    workspace_value = (
        _clean_entered_value(args.workspace)
        if args.workspace
        else _select_workspace_interactively()
    )
    if args.student_canvas_submissions:
        submissions_value = args.student_canvas_submissions
    elif questionary is None:
        submissions_value = _clean_entered_value(
            input("Student-canvas-submissions ZIP: ")
        )
    else:
        submissions_value = questionary.path("Student-canvas-submissions ZIP:").ask()
        if submissions_value is None:
            raise ValueError("Student-canvas-submissions prompt was cancelled.")
        submissions_value = _clean_entered_value(submissions_value)
    if args.required_file:
        required_file = args.required_file
    elif questionary is None:
        required_file = _clean_entered_value(input("Required student filename: "))
    else:
        required_file = questionary.text("Required student filename:").ask()
        if required_file is None:
            raise ValueError("Required filename prompt was cancelled.")
        required_file = _clean_entered_value(required_file)
    optional_files = args.optional_files
    if optional_files is None:
        if questionary is None:
            optional_value = input("Optional files [README.md]: ")
        else:
            optional_value = questionary.text(
                "Optional files (comma-separated) [README.md]:"
            ).ask()
            if optional_value is None:
                raise ValueError("Optional files prompt was cancelled.")
            optional_value = optional_value.strip()
        optional_files = [
            _clean_entered_value(item)
            for item in optional_value.split(",")
            if _clean_entered_value(item)
        ] or ["README.md"]
    if not workspace_value or not submissions_value or not required_file:
        raise ValueError("Workspace, student-canvas-submissions, and required filename are required.")
    workspace_root = Path(workspace_value).expanduser()
    workspace_config = workspace_root / "workspace.json"
    if not workspace_config.is_file():
        raise FileNotFoundError(
            f"Workspace '{workspace_root}' is not initialized; run create-workspace first."
        )
    result = SubmissionImporter(
        submissions_value,
        workspace_root,
        required_filename=required_file,
        optional_filenames=optional_files,
    ).import_submissions()
    _print_import_result(result)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the grading CLI while preserving the legacy milestone commands.

    :param argv: Arguments to parse, or ``sys.argv[1:]`` when omitted.
    :return: Zero after the selected command completes.
    """
    command_arguments = list(sys.argv[1:] if argv is None else argv)
    if command_arguments and command_arguments[0] == "create-workspace":
        return create_workspace(command_arguments[1:])
    if command_arguments and command_arguments[0] in {
        "import-student-canvas-submissions", "import-submissions"
    }:
        return import_submissions(command_arguments[1:])

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
