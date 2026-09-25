"""
Matching expected output for our supplied testcases
Run unpublished testcases with expected output (we never got around to this)

Global variables

[x] bash script (`find_hpp.sh` returns none): Lack of header files (all code in one file)
"""

import config
from tools import util

import argparse
import json
import os
import re
import shlex
import sys
from pathlib import Path
from collections.abc import Callable
from typing import Sequence

from core.workspace import Workspace, create_workspace as initialize_workspace
from core.submission_importer import ImportResult, SubmissionImporter
from core.teacher_importer import TeacherImportResult, TeacherImporter
from core.workspace_reporter import WorkspaceReportResult, WorkspaceReporter
from core.submission_names import format_submission_label, load_submission_names
from core.similarity import SimilarityAnalyzer, temporary_source_index
from core.report_index import (
    create_buildtime_log_index,
    create_file_index,
    create_report_index,
    create_runtime_log_index,
    ReportIndexResult,
)

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
        "filepath_arg", nargs="?",
        help="Path relative to each report directory; prompts if omitted",
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
    parser.add_argument(
        "--required-file",
        action="append",
        dest="required_files",
        help="Required student filename; may be repeated",
    )
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
    if result.summary:
        print(f"Import summary: {result.summary}")
    names = load_submission_names(result.summary.parent) if result.summary else {}
    for submission in result.submissions:
        print(
            f"  {format_submission_label(submission.identifier, names)}: "
            f"{submission.workspace}"
        )
        for warning in submission.warnings:
            print(f"    warning: {warning}")
    for warning in result.warnings:
        if not any(warning.endswith(item) for submission in result.submissions for item in submission.warnings):
            print(f"warning: {warning}")


def _print_import_command(
    workspace: str,
    student_canvas_submissions: str,
    required_files: list[str],
    optional_files: list[str],
) -> None:
    """Print a shell command equivalent to the completed import prompts.

    :param workspace: Selected or entered workspace directory.
    :param student_canvas_submissions: Student-canvas-submissions ZIP path.
    :param required_files: Required student filenames accepted during import.
    :param optional_files: Optional filenames accepted during import.
    """
    command = [
        "python3",
        "main.py",
        "import-student-canvas-submissions",
        "--workspace",
        workspace,
        "--student-canvas-submissions",
        student_canvas_submissions,
    ]
    for required_file in required_files:
        command.extend(("--required-file", required_file))
    for optional_file in optional_files:
        command.extend(("--optional-file", optional_file))
    print(f"Equivalent command: {shlex.join(command)}")


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


def _existing_submissions(workspace: str | Path) -> list[str]:
    """Find normalized submission identifiers in a grading workspace.

    :param workspace: Initialized grading workspace to inspect.
    :return: Sorted submission directory names containing submission metadata.
    """
    students_root = Path(workspace).expanduser() / "students"
    if not students_root.is_dir():
        return []
    return sorted(
        path.name
        for path in students_root.iterdir()
        if path.is_dir() and (path / "submission_metadata.json").is_file()
    )


def _select_submission_interactively(workspace: str | Path) -> list[str] | None:
    """Choose all submissions or several submissions for an interactive report.

    :param workspace: Initialized grading workspace containing submissions.
    :return: Selected identifiers, or ``None`` to report all submissions.
    :raises ValueError: If the selection is cancelled or invalid.
    """
    submissions = _existing_submissions(workspace)
    if not submissions:
        return None
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        selection = input("Grade all submissions? [Y/n]: ").strip().lower()
        if not selection or selection in {"y", "yes"}:
            return None
        return _select_submission_numbers(submissions, workspace)
    else:
        try:
            import questionary
        except ImportError:
            selection = input("Grade all submissions? [Y/n]: ").strip().lower()
            if not selection or selection in {"y", "yes"}:
                return None
            return _select_submission_numbers(submissions, workspace)
        grade_all = questionary.confirm(
            "Grade all submissions?", default=True
        ).ask()
        if grade_all is None:
            raise ValueError("Submission selection was cancelled.")
        if grade_all:
            return None
        selected = questionary.checkbox(
            "Select submissions to grade:",
            choices=[
                questionary.Choice(
                    format_submission_label(item, load_submission_names(workspace)),
                    value=item,
                )
                for item in submissions
            ],
        ).ask()
        if selected is None:
            raise ValueError("Submission selection was cancelled.")
        if not selected:
            raise ValueError("Select at least one submission.")
        return selected


def _select_submission_numbers(
    submissions: list[str], workspace: str | Path
) -> list[str]:
    """Select one or more submissions using comma-separated list numbers.

    :param submissions: Available normalized submission identifiers.
    :param workspace: Grading workspace containing the mapping CSV.
    :return: Selected submission identifiers.
    :raises ValueError: If the selection is invalid.
    """
    print("Select submissions (comma-separated numbers):")
    names = load_submission_names(workspace)
    for index, submission in enumerate(submissions, start=1):
        print(f"  {index}. {format_submission_label(submission, names)}")
    selection = input("Submission numbers: ").strip()
    if not selection:
        raise ValueError("Select at least one submission.")
    try:
        selected_indices = [int(value.strip()) - 1 for value in selection.split(",")]
    except ValueError as error:
        raise ValueError("Submission selections must be numbers separated by commas.") from error
    if any(index < 0 or index >= len(submissions) for index in selected_indices):
        raise ValueError("Submission selection is out of range.")
    return list(dict.fromkeys(submissions[index] for index in selected_indices))


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
    workspace_root = Path(workspace_value).expanduser()
    workspace_config = workspace_root / "workspace.json"
    if not workspace_config.is_file():
        raise FileNotFoundError(
            f"Workspace '{workspace_root}' is not initialized; run create-workspace first."
        )
    workspace_metadata = json.loads(workspace_config.read_text(encoding="utf-8"))
    configured_submission: dict[str, object] = {}
    configuration_path = workspace_metadata.get("milestone_configuration")
    if isinstance(configuration_path, str) and configuration_path:
        milestone_config = config.load_config(
            str(workspace_metadata.get("milestone", "workspace")),
            Path(configuration_path),
        )
        submission_value = milestone_config.get("submission", {})
        if isinstance(submission_value, dict):
            configured_submission = submission_value
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
    configured_required = configured_submission.get("required_files", [])
    structured_submissions = bool(configured_submission)
    required_files = (
        [str(item) for item in configured_required if isinstance(item, str)]
        if isinstance(configured_required, list) else []
    )
    if args.required_files:
        required_files = args.required_files
        required_file = required_files[0]
    elif required_files:
        required_file = required_files[0]
    elif questionary is None:
        required_file = _clean_entered_value(input("Required student filename: "))
        required_files = [required_file]
    else:
        required_file = questionary.text("Required student filename:").ask()
        if required_file is None:
            raise ValueError("Required filename prompt was cancelled.")
        required_file = _clean_entered_value(required_file)
        required_files = [required_file]
    optional_files = args.optional_files
    configured_optional = configured_submission.get("optional_files", [])
    if optional_files is None and isinstance(configured_optional, list):
        optional_files = [str(item) for item in configured_optional if isinstance(item, str)]
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
    if not workspace_value or not submissions_value:
        raise ValueError("Workspace and student-canvas-submissions are required.")
    _print_import_command(
        workspace_value,
        submissions_value,
        required_files,
        optional_files,
    )
    result = SubmissionImporter(
        submissions_value,
        workspace_root,
        required_filename=required_file or None,
        optional_filenames=optional_files,
        required_filenames=required_files,
        structured_submissions=structured_submissions,
    ).import_submissions()
    _print_import_result(result)
    return 0


def _import_teacher_parser() -> argparse.ArgumentParser:
    """Build the parser for importing teacher materials.

    :return: Parser describing teacher-archive import options.
    """
    parser = argparse.ArgumentParser(
        prog="Grade Checker import-teacher-zip",
        description="Import a teacher ZIP and its student template into a workspace.",
    )
    parser.add_argument("--workspace", help="Initialized grading workspace directory")
    parser.add_argument("--teacher-zip", help="Teacher ZIP archive")
    parser.add_argument(
        "--template-zip",
        help="Exact path of the student-template ZIP inside the teacher archive; prompts if omitted",
    )
    return parser


def _print_teacher_import_result(result: TeacherImportResult) -> None:
    """Print a human-readable summary of imported teacher materials.

    :param result: Teacher import result to summarize.
    """
    print(f"Teacher archive preserved at: {result.raw_archive}")
    print(f"Template ZIP: {result.template_member}")
    print(
        f"Template files imported to: {result.template_root} "
        f"({len(result.template_files)} files)"
    )
    print(
        f"Teacher reference files imported to: {result.reference_root} "
        f"({len(result.reference_files)} files)"
    )
    print(f"Import metadata written to: {result.metadata_path}")


def import_teacher_zip(arguments: Sequence[str]) -> int:
    """Import teacher-only artifacts into an initialized grading workspace.

    :param arguments: Arguments following ``import-teacher-zip``.
    :return: Zero after a successful import.
    :raises FileNotFoundError: If the archive or workspace is absent.
    :raises ValueError: If either archive is invalid or unsafe.
    """
    args = _import_teacher_parser().parse_args(list(arguments))
    try:
        import questionary
    except ImportError:
        questionary = None

    workspace_value = (
        _clean_entered_value(args.workspace)
        if args.workspace
        else _select_workspace_interactively()
    )
    if args.teacher_zip:
        teacher_zip_value = _clean_entered_value(args.teacher_zip)
    elif questionary is None:
        teacher_zip_value = _clean_entered_value(input("Teacher ZIP: "))
    else:
        teacher_zip_value = questionary.path("Teacher ZIP:").ask()
        if teacher_zip_value is None:
            raise ValueError("Teacher ZIP prompt was cancelled.")
        teacher_zip_value = _clean_entered_value(teacher_zip_value)

    if not workspace_value or not teacher_zip_value:
        raise ValueError("Workspace and teacher ZIP are required.")

    importer = TeacherImporter(teacher_zip_value, workspace_value, args.template_zip or "")
    template_member = args.template_zip or _select_template_member(importer)
    result = TeacherImporter(
        teacher_zip_value, workspace_value, template_member
    ).import_teacher_archive()
    _print_teacher_import_result(result)
    return 0


def _select_template_member(importer: TeacherImporter) -> str:
    """Select a nested student-template ZIP from teacher-archive candidates.

    :param importer: Teacher archive importer used to discover candidates.
    :return: Selected nested ZIP member name.
    :raises ValueError: If no candidate exists or the selection is cancelled
        or invalid.
    """
    candidates = importer.find_template_members()
    if not candidates:
        raise ValueError("The teacher archive contains no nested ZIP template candidates.")
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Select the student template ZIP:")
        for index, candidate in enumerate(candidates, start=1):
            print(f"  {index}. {candidate}")
        selection = input("Template ZIP number: ").strip()
        try:
            selected_index = int(selection) - 1
        except ValueError as error:
            raise ValueError("Template ZIP selection must be a number.") from error
        if selected_index < 0 or selected_index >= len(candidates):
            raise ValueError("Template ZIP selection is out of range.")
        return candidates[selected_index]

    try:
        import questionary
    except ImportError:
        return candidates[0] if len(candidates) == 1 else _select_template_member_numbered(candidates)
    selected = questionary.select(
        "Select the student template ZIP:", choices=candidates
    ).ask()
    if selected is None:
        raise ValueError("Template ZIP selection was cancelled.")
    return selected


def _select_template_member_numbered(candidates: list[str]) -> str:
    """Select a template ZIP using a numbered fallback prompt.

    :param candidates: Candidate nested template ZIP member names.
    :return: Selected member name.
    :raises ValueError: If the entered selection is invalid.
    """
    for index, candidate in enumerate(candidates, start=1):
        print(f"  {index}. {candidate}")
    selection = input("Template ZIP number: ").strip()
    try:
        selected_index = int(selection) - 1
    except ValueError as error:
        raise ValueError("Template ZIP selection must be a number.") from error
    if selected_index < 0 or selected_index >= len(candidates):
        raise ValueError("Template ZIP selection is out of range.")
    return candidates[selected_index]


def _report_parser() -> argparse.ArgumentParser:
    """Build the parser for the explicit reporting command.

    :return: Parser describing the legacy milestone reporting workflow.
    """
    parser = argparse.ArgumentParser(
        prog="Grade Checker report",
        description="Generate reports for an initialized grading workspace.",
    )
    parser.add_argument(
        "--workspace",
        help="Initialized grading workspace directory; prompts if omitted",
    )
    parser.add_argument(
        "--submission",
        action="append",
        help="Report one or more normalized submission identifiers; repeat the option",
    )
    parser.add_argument(
        "--code-analyzer",
        help="CodeAnalyzer.cpp or its containing directory",
    )
    return parser


def _analyze_parser() -> argparse.ArgumentParser:
    """Build the parser for the standalone similarity-analysis command.

    :return: Parser describing workspace and CodeAnalyzer options.
    """
    parser = argparse.ArgumentParser(
        prog="Grade Checker analyze-similarity",
        description="Run CodeAnalyzer without running the grading reporter.",
    )
    parser.add_argument(
        "--workspace",
        help="Initialized grading workspace directory; prompts if omitted",
    )
    parser.add_argument(
        "--code-analyzer",
        help="CodeAnalyzer.cpp or its containing directory; discovers the default when omitted",
    )
    return parser


def analyze(arguments: Sequence[str]) -> int:
    """Run CodeAnalyzer independently against workspace submissions.

    :param arguments: Arguments following ``analyze-similarity``.
    :return: Zero after the similarity report is written.
    :raises FileNotFoundError: If the workspace or analyzer cannot be found.
    :raises RuntimeError: If CodeAnalyzer compilation or execution fails.
    :raises ValueError: If the analyzer source is invalid.
    """
    args = _analyze_parser().parse_args(list(arguments))
    workspace = Path(
        _clean_entered_value(args.workspace)
        if args.workspace
        else _select_workspace_interactively()
    ).expanduser()
    if not (workspace / "workspace.json").is_file():
        raise FileNotFoundError(
            f"Workspace '{workspace}' is not initialized; run create-workspace first."
        )
    students_root = workspace / "students"
    if not students_root.is_dir():
        raise FileNotFoundError(
            f"Workspace students directory '{students_root}' was not found."
        )
    analyzer_path = (
        Path(args.code_analyzer).expanduser()
        if args.code_analyzer
        else WorkspaceReporter._find_repository_analyzer()
    )
    if analyzer_path is None:
        raise FileNotFoundError(
            "CodeAnalyzer was not found; provide --code-analyzer with its path."
        )
    output_path = workspace / "similarity-report.txt"
    analyzer = SimilarityAnalyzer(analyzer_path)
    with temporary_source_index(students_root) as source_index:
        analyzer.run(source_index, output_path)
    print(f"Similarity report: {_display_workspace_path(workspace, output_path)}")
    return 0


def _report_index_parser() -> argparse.ArgumentParser:
    """Build the parser for the generate-index-report command.

    :return: Parser describing generate-index-report options.
    """
    parser = argparse.ArgumentParser(
        prog="Grade Checker generate-index-report",
        description="Create a symlink index for reports in a grading workspace.",
    )
    parser.add_argument(
        "--workspace",
        help="Initialized grading workspace directory; prompts if omitted",
    )
    parser.add_argument(
        "--output",
        help="Index directory; defaults to <workspace>/report-index",
    )
    return parser


def report_index(arguments: Sequence[str]) -> int:
    """Create a symlink index for all reports in a grading workspace.

    :param arguments: Arguments following ``generate-index-report``.
    :return: Zero after the index is created.
    """
    args = _report_index_parser().parse_args(list(arguments))
    workspace = args.workspace or _select_workspace_interactively()
    result = create_report_index(workspace, args.output)
    print(f"Report index: {result.directory}")
    print(f"Report links created: {len(result.links)}")
    return 0


def _index_file_choices(workspace: str | Path) -> list[str]:
    """Collect standard report files and required student files.

    :param workspace: Initialized grading workspace to inspect.
    :return: Unique relative paths suitable for the index prompt.
    """
    choices = [
        "report.txt",
        "build-output.log",
        "runtime-output.log",
        "notes.md",
        "overrides.json",
    ]
    students_root = Path(workspace).expanduser() / "students"
    if students_root.is_dir():
        for metadata_path in sorted(students_root.glob("*/submission_metadata.json")):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            required_files = metadata.get("required_files", [])
            if isinstance(required_files, list):
                choices.extend(
                    str(filename) for filename in required_files
                    if isinstance(filename, str) and filename
                )
    return list(dict.fromkeys(choices))


def _select_index_file_interactively(workspace: str | Path) -> str:
    """Ask which standard or required file should be indexed.

    :param workspace: Initialized grading workspace to inspect.
    :return: Selected filepath relative to each report directory.
    :raises ValueError: If the prompt is cancelled or no file is selected.
    """
    choices = _index_file_choices(workspace)
    try:
        import questionary
    except ImportError:
        questionary = None
    if questionary is not None and sys.stdin.isatty() and sys.stdout.isatty():
        selected = questionary.select("File to index:", choices=choices).ask()
        if selected is None:
            raise ValueError("File selection was cancelled.")
        return selected
    print("Select a file to index:")
    for index, choice in enumerate(choices, start=1):
        print(f"  {index}. {choice}")
    selection = input("File number: ").strip()
    try:
        selected_index = int(selection) - 1
    except ValueError as error:
        raise ValueError("File selection must be a number.") from error
    if selected_index < 0 or selected_index >= len(choices):
        raise ValueError("File selection is out of range.")
    return choices[selected_index]


def _index_parser() -> argparse.ArgumentParser:
    """Build the parser for the general file index command.

    :return: Parser describing ``generate-index`` options.
    """
    parser = argparse.ArgumentParser(
        prog="Grade Checker generate-index",
        description="Create a symlink index for one file from each submission.",
    )
    parser.add_argument(
        "filepath_arg", nargs="?",
        help="Path relative to each report directory; prompts if omitted",
    )
    parser.add_argument(
        "--workspace",
        help="Initialized grading workspace directory; prompts if omitted",
    )
    parser.add_argument(
        "--file", "--filepath", dest="filepath",
        help="Path relative to each report directory; prompts if omitted",
    )
    parser.add_argument(
        "--output",
        help="Index directory; defaults to <workspace>/<filename>-index",
    )
    return parser


def generate_index(arguments: Sequence[str]) -> int:
    """Create an index for a selected file across all submission reports.

    :param arguments: Arguments following ``generate-index``.
    :return: Zero after the index is created.
    """
    args = _index_parser().parse_args(list(arguments))
    workspace = args.workspace or _select_workspace_interactively()
    filepath = args.filepath or args.filepath_arg or _select_index_file_interactively(workspace)
    result = create_file_index(workspace, filepath, args.output)
    print(f"Index: {result.directory}")
    print(f"Links created: {len(result.links)}")
    return 0


def _log_index_parser(command: str, default_directory: str) -> argparse.ArgumentParser:
    """Build the parser shared by runtime-log and buildtime-log index commands.

    :param command: CLI command name shown in help and error messages.
    :param default_directory: Default workspace-relative output directory.
    :return: Parser describing log index options.
    """
    parser = argparse.ArgumentParser(
        prog=f"Grade Checker {command}",
        description=f"Create a symlink index for {command.removeprefix('generate-index-')} logs.",
    )
    parser.add_argument(
        "--workspace",
        help="Initialized grading workspace directory; prompts if omitted",
    )
    parser.add_argument(
        "--output",
        help=f"Index directory; defaults to <workspace>/{default_directory}",
    )
    return parser


def _log_index(
    arguments: Sequence[str],
    command: str,
    default_directory: str,
    create_index: Callable[[str | Path, str | Path | None], ReportIndexResult],
    label: str,
) -> int:
    """Create a symlink index for one category of submission logs.

    :param arguments: Arguments following the selected CLI command.
    :param command: CLI command name used to parse arguments.
    :param default_directory: Default workspace-relative output directory.
    :param create_index: Index factory accepting workspace and output paths.
    :param label: Human-readable label printed after creation.
    :return: Zero after the index is created.
    """
    args = _log_index_parser(command, default_directory).parse_args(list(arguments))
    workspace = args.workspace or _select_workspace_interactively()
    result = create_index(workspace, args.output)
    print(f"{label} log index: {result.directory}")
    print(f"Log links created: {len(result.links)}")
    return 0


def runtime_log_index(arguments: Sequence[str]) -> int:
    """Create a symlink index for all submission runtime logs.

    :param arguments: Arguments following the runtime log index command.
    :return: Zero after the index is created.
    """
    return _log_index(
        arguments, "generate-index-runtime-log", "runtime-log-index",
        create_runtime_log_index, "Runtime"
    )


def buildtime_log_index(arguments: Sequence[str]) -> int:
    """Create a symlink index for all submission buildtime logs.

    :param arguments: Arguments following the buildtime log index command.
    :return: Zero after the index is created.
    """
    return _log_index(
        arguments, "generate-index-buildtime-log", "buildtime-log-index",
        create_buildtime_log_index, "Buildtime"
    )


def _select_code_analyzer_interactively(
    default: Path | None, workspace: Path
) -> Path | None:
    """Ask whether an interactive report should run CodeAnalyzer.

    :param default: Analyzer discovered in the grader repository, if present.
    :param workspace: Workspace root used for consistent path display.
    :return: Selected analyzer path, or ``None`` to skip similarity analysis.
    """
    choices = []
    default_choice = "Use default CodeAnalyzer"
    if default is not None:
        display_path = _display_workspace_path(workspace, default)
        default_choice = f"Use default CodeAnalyzer ({display_path})"
        choices.append(default_choice)
    choices.extend(("Specify a custom CodeAnalyzer path", "Skip similarity analysis"))
    try:
        import questionary
    except ImportError:
        questionary = None
    if questionary is not None:
        choice = questionary.select(
            "Similarity analyzer:", choices=choices, default=choices[0]
        ).ask()
    else:
        print("Similarity analyzer options:")
        for index, choice_text in enumerate(choices, start=1):
            print(f"  {index}. {choice_text}")
        choice = choices[int(input("Choose an option: ").strip() or "1") - 1]
    if choice == default_choice:
        return default
    if choice == "Specify a custom CodeAnalyzer path":
        if questionary is not None:
            value = questionary.path("CodeAnalyzer path:").ask()
        else:
            value = input("CodeAnalyzer path: ").strip()
        if not value:
            raise ValueError("A custom CodeAnalyzer path is required.")
        return Path(value).expanduser()
    return None


def report(arguments: Sequence[str]) -> int:
    """Generate reports for submissions in a grading workspace.

    :param arguments: Arguments following ``report``.
    :return: Zero after reporting completes.
    """
    args = _report_parser().parse_args(list(arguments))
    interactive_workspace = not args.workspace
    workspace = (
        _clean_entered_value(args.workspace)
        if args.workspace
        else _select_workspace_interactively()
    )
    submission = args.submission
    if submission is None and interactive_workspace:
        submission = _select_submission_interactively(workspace)
    reporter = WorkspaceReporter(workspace)
    if args.code_analyzer:
        reporter.code_analyzer_path = Path(args.code_analyzer).expanduser()
    elif interactive_workspace:
        reporter.code_analyzer_path = _select_code_analyzer_interactively(
            WorkspaceReporter._find_repository_analyzer(), Path(workspace)
        )
        reporter.disable_code_analyzer = reporter.code_analyzer_path is None
    result = reporter.report(submission=submission)
    _print_workspace_report_result(result)
    return 0


def _print_workspace_report_result(result: WorkspaceReportResult) -> None:
    """Print the locations of reports generated for a workspace.

    :param result: Workspace report result to summarize.
    """
    print(f"Workspace path prefix: {result.workspace}")
    print(f"Workspace reports generated: {len(result.reports)}")
    for report_path in result.reports:
        print(f"  Report: {_display_workspace_path(result.workspace, report_path)}")
    print(f"Summary report: {_display_workspace_path(result.workspace, result.summary)}")
    print(
        "Similarity report: "
        f"{_display_workspace_path(result.workspace, result.similarity_report)}"
    )


def _display_workspace_path(workspace: Path, path: Path) -> str:
    """Render a workspace path using a short, recoverable display form.

    :param workspace: Absolute workspace root printed as the path prefix.
    :param path: Path inside the workspace to render.
    :return: Path rendered relative to the workspace with a
        ``<workspace-path>/`` hint.
    """
    relative = Path(os.path.relpath(path, workspace)).as_posix()
    return f"<workspace-path>/{relative}"


def _run_report(milestone: str, cfg: config.Config) -> None:
    """Run the existing repository reporting workflow.

    :param milestone: Base milestone name used by the reporter.
    :param cfg: Loaded milestone configuration consumed by the reporter.
    """
    from core.reporter2 import Reporter2

    print("main: Entered Reporter.")
    reporter = Reporter2(milestone, cfg)
    reporter._report()
    reporter.report()


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
    if command_arguments and command_arguments[0] in {
        "import-teacher-zip", "import-teacher"
    }:
        return import_teacher_zip(command_arguments[1:])
    if command_arguments and command_arguments[0] == "report":
        return report(command_arguments[1:])
    if command_arguments and command_arguments[0] == "analyze-similarity":
        return analyze(command_arguments[1:])
    if command_arguments and command_arguments[0] == "generate-index-report":
        return report_index(command_arguments[1:])
    if command_arguments and command_arguments[0] == "generate-index":
        return generate_index(command_arguments[1:])
    if command_arguments and command_arguments[0] in {
        "generate-index-runtime-log", "generate-index-runtime"
    }:
        return runtime_log_index(command_arguments[1:])
    if command_arguments and command_arguments[0] in {
        "generate-index-buildtime-log", "generate-index-buildtime"
    }:
        return buildtime_log_index(command_arguments[1:])

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
        # Compatibility path for existing scripts. New invocations should use
        # `python3 main.py report <milestone>` instead.
        _run_report(milestone, cfg)
        # xxx we always build. keep track of what's already built to not build
        # again.



        
    return 0


if __name__ == "__main__":
    main()
