# Grade Checker

## Versioning and changelogs

The current application version is stored in [`VERSION`](VERSION); the current
development line is v2.2. User-facing changes are tracked in
[`CHANGELOG.md`](CHANGELOG.md) under `Unreleased` while development continues.

The AI maintainer is expected to update the `Unreleased` changelog as part of
normal work. It must ask before changing the application version or preparing a
numbered release. A release may contain features and bug fixes together; the
version reflects the largest user-facing impact of the combined changes.

The `workspace_version` value in generated `workspace.json` files is separate
and changes only when the workspace file layout or metadata schema changes.

## Usage
### Setup:
#### python
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The interactive workspace selector uses `questionary`, which is installed by
the requirements above.

#### env
```bash
USERNAME=${github_username}
PAT=${github_personal_access_token} # generate from github settings
ORGANIZATION=${organization_for_grading}
FETCH_DATE=${cutoff_date_to_fetch_repos_after}  # format: YYYY-MM-DD
TRIM_REPO=${xxx}
# xxx having to modify fetch date for initial submissions (and later
# resubmissions) here is awkward, but WORKS. better solution is bake the dates
# into the json config for (1) initial submission and (2) resubmission, so they
# don't need to be adjusted.
```

### fetch repos:
```bash
# xxx could add this cleanup into the infra, but that would be destructive and
# doesn't allow easy "dry" runs. either way, this should be automated into the
# infra. SOLUTION: add a "reset" to the _milestoneX.jsons
rm -rvf repos/milestone${num}-${prof}   # clear old repos
mkdir -p repos/milestone${num}-${prof} # make dir to fetch repos into
python main.py milestone${num}-${prof} -f
# xxx naming mismatch in fetch vs. reports dirs is because of changing infra
# that was hacked instead of reconciled. this should be aligned. problem lies in
# different config expansions
```

#### update to new org
update in .env and update per milestone in milestones/_milestone${num}-${prof}

### grade and report:
```bash
rm -rvf repos/milestone${num}   # clear old reports
mkdir -p repos/milestone${num}/reports
python main.py milestone${num}-${prof} -r
```

### Create a grading workspace

Initialize an empty grading workspace interactively:

```bash
python3 main.py create-workspace
```

During interactive creation, CSV files found directly in
`grading-workspaces/` are offered with an arrow-key selector. You can choose a
default, enter another file, or continue without a mapping. A selected file
is recorded as the workspace's external mapping source; it is not copied into
the workspace. For scripted creation, provide it explicitly:

```bash
python3 main.py create-workspace \
  --output grading-workspaces/milestone2 \
  --identifier-file student-identifiers.csv
```

The identifier file must have the columns
`submission_identifier,human_readable_name`. The source path is recorded in
`workspace.json`, so moving or deleting the source file requires updating the
workspace configuration or recreating the workspace.

For scripted use, provide the values as options:

```bash
python3 main.py create-workspace \
  --output grading-workspaces/milestone2 \
  --milestone milestone2-hugh
```

### Import student-canvas-submissions

After creating a workspace, import student-canvas-submissions interactively:

```bash
python3 main.py import-student-canvas-submissions
```

The command prompts for the initialized workspace, the
student-canvas-submissions ZIP, the required student filename, optional files,
and which submissions to import. `README.md` is the default optional file.

After the prompts are complete, the CLI prints an equivalent shell command so
the same import can be rerun quickly without interactive prompts.

When run in a terminal, use the Up/Down arrow keys to choose an existing
initialized workspace under `grading-workspaces/`, or select the custom-path
option to enter any workspace directory manually. Non-interactive terminals
use a numbered selection instead.

For scripted use:

```bash
python3 main.py import-student-canvas-submissions \
  --workspace grading-workspaces/milestone2 \
  --student-canvas-submissions student-canvas-submissions.zip \
  --required-file milestone2.cpp \
  --submission student_123
```

Repeat `--submission` to import several selected submissions. If the option is
omitted in an interactive terminal, the importer first asks whether all
submissions should be imported and displays a checklist only when the answer is
no. Non-interactive runs continue to import all submissions by default.

The importer is also available from Python as
`core.submission_importer.SubmissionImporter`. It preserves the input ZIP under
`raw/`, creates normalized student directories under `students/`, and writes
`submission_metadata.json` beside each student's `src-files/` directory. For
structured milestones, required and optional student files are read from the
milestone configuration's `submission` section:

```json
"submission": {
  "required_files": ["HashTable.cpp", "HashTable.hpp"],
  "optional_files": ["README.md"]
}
```

Milestone 2 supports three submission formats. Direct Canvas files are
imported with a no-ZIP warning; a ZIP with files at its archive root is
imported with a flat-layout warning; and a ZIP with one top-level project
directory is the preferred layout. Configured source files are copied to
`src-files/`, direct UML matches are copied to `uml-diagrams/`, and additional
files are warned about. Missing or misplaced UML files are retained as
manual-review warnings in `submission_metadata.json`; they do not prevent
source grading. macOS metadata such as `__MACOSX`, `.DS_Store`, and `._*`
entries is ignored during layout detection.

Each import also writes `import-summary.md` at the workspace root. The summary
lists the import status, required-file counts, UML status, copied-file counts,
and manual-review warnings for every submission.

The workspace may use an external identifier mapping with the columns
`submission_identifier,human_readable_name`. Fill in the second column to give
submissions readable names. The selected source path is recorded in
`workspace.json`; the mapping file itself is not copied. Existing workspaces
with a local `submission-identifiers.csv` continue to work. The Canvas-
generated identifier remains the stable directory and command-line key, while
user-facing import and reporting output uses the readable name when available.

Legacy milestones continue to support the existing single-file recovery path.

When Canvas exports multiple files submitted by the same student, the importer
groups files with the same Canvas-generated metadata prefix into one normalized
submission workspace. Internal identifiers contain only the student name and
the first numeric Canvas metadata component. The optional `[LATE]` marker,
per-file numeric metadata, and uploaded filename are ignored for that
identifier. The required file and allowed optional files are copied there;
other files are retained in the source metadata and reported as warnings.

When reporting runs, each submission receives an isolated directory under
`build-workspaces/`. The teacher template is copied there first and the
student files are overlaid afterward. Submission metadata records the teacher
files, student files, and any template files replaced by the student.

### Import teacher materials

Import the teacher ZIP after creating a workspace. The command interactively
prompts for the workspace, teacher ZIP, and nested student-template ZIP. In a
terminal, workspace and template choices use keyboard-navigable select prompts.
The options can be supplied when scripting; `--template-zip` must be the exact
member path of the student-template ZIP inside the teacher archive:

```bash
python3 main.py import-teacher-zip \
  --workspace grading-workspaces/milestone2 \
  --teacher-zip teacher-materials.zip \
  --template-zip student-template.zip
```

The command preserves the teacher archive under `raw/`, extracts all other
teacher files under `references/teacher/`, extracts the selected template under
`references/template/`, and writes `references/teacher_metadata.json`. Template
files ending in `.grader-ignore` are excluded.

### Reporting

Run the workspace reporter interactively:

```bash
python3 main.py report
```

It selects an initialized workspace, prepares each submission's build
workspace at report time, and writes per-submission reports directly inside
each `students/<submission>/` directory. The summary is written to
`report-summary.md` at the workspace root and contains submission,
build, and runtime statuses plus method and required-file counts. For scripted
runs, provide the workspace directly. Each reporting command also writes a
submission-only snapshot under `runs/`; `runs/summary-state.json` keeps the
latest known row for every submission.

Each `students/<submission>/` directory contains `src-files/`, metadata,
reports, logs, notes, and overrides for that student.

The reporter compares captured student stdout with the first TA-provided
output reference in `references/teacher/`. The summary records whether it is
an `exact match`, differs only by empty lines, or requires `manual review`.
It also reports the number of differing substantive lines; empty-line-only
differences count as zero.
Case-only, whitespace-only, and combined case/whitespace differences are
accepted and listed separately in the comparison column.

```bash
python3 main.py report --workspace grading-workspaces/milestone2
```

To report one normalized submission from a scripted run:

```bash
python3 main.py report \
  --workspace grading-workspaces/milestone2 \
  --submission student01
```

Repeat `--submission` to report a selected group of submissions.

To create a directory of convenient symlinks to the generated reports:

```bash
python3 main.py generate-index-report
```

The command interactively selects an initialized workspace when
`--workspace` is omitted. For scripted use, provide the workspace explicitly:

```bash
python3 main.py generate-index-report \
  --workspace grading-workspaces/milestone2
```

This creates `report-index/` by default, with one link per submission report
plus links to `report-summary.md` and `similarity-report.txt` when those files exist.
Links are relative, so the workspace can be moved. Re-running the command
refreshes existing symlinks and does not overwrite real files.
Use `--name-by mapped` to use `submission-identifiers.csv` display names for
submission links. Add `--include-extension` to append the original target
extension to each link name.

The general index command accepts one or more file or directory paths relative
to each student's directory:

```bash
python3 main.py generate-index notes.md \
  --workspace grading-workspaces/milestone2
```

It can also be supplied with `--file` (or `--filepath`). With no filepath, the
interactive command offers standard report files (`report.txt`, both logs,
`notes.md`, and `overrides.json`), directories found in student submissions
(such as `src-files/` and `uml-diagrams/`), and configured required student
submission files. Required student files are linked from each student's
`src-files/` directory.
Repeat `--file` to index multiple paths in one directory. For a multi-file
index, links use names such as `student01-notes.md` and
`student01-overrides.json` so the targets remain distinct. The default output
directory for a multi-file index is `index/`.
Pass `--group-by-submission` to put those links under directories instead,
such as `index/student01/notes.md` and `index/student01/overrides.json`.
The directory name follows `--name-by identifier` or `--name-by mapped`.
When selecting files interactively, grouping is asked in its own prompt before
the mapped-name and extension options.
All index commands accept `--name-by identifier` (the default) or
`--name-by mapped`. Add `--include-extension` when link names should include
the original target extension, such as `Ada Lovelace.cpp` or
`Ada Lovelace.txt`.
When these flags are omitted in an interactive terminal, an arrow-navigable
checklist lets you independently select mapped names and extension appending.

The previous specialized log commands remain available as shortcuts:

```bash
python3 main.py generate-index-runtime-log \
  --workspace grading-workspaces/milestone2
python3 main.py generate-index-buildtime-log \
  --workspace grading-workspaces/milestone2
```

These create `runtime-output.log-index/` and `build-output.log-index/` by
default, respectively, with one link per submission. The aliases
`generate-index-runtime` and `generate-index-buildtime` are also supported.
Use `--output` to choose a different index directory.

These create `runtime-log-index/` and `buildtime-log-index/` by default,
respectively, with one link per submission. The aliases
`generate-index-runtime` and `generate-index-buildtime` are also supported.
The general command defaults to `index/`. Use `--output` to choose a different
index directory.

When `report` is run without `--workspace`, the interactive workflow asks
whether to report all submissions or select one or more from the workspace.
Reporting all submissions is the default.

The reporter first looks for an optional `CodeAnalyzer/CodeAnalyzer.cpp` or
`CodeAnalyzer.cpp` in the root of the grader repository. If it is not present,
similarity analysis is recorded as not run. An explicit path can also be
provided:

```bash
python3 main.py report \
  --workspace grading-workspaces/milestone2 \
  --code-analyzer /path/to/CodeAnalyzer
```

To run only the similarity analyzer, without rebuilding submissions or
rewriting `report-summary.md`, use:

```bash
python3 main.py analyze-similarity \
  --workspace grading-workspaces/milestone2 \
  --code-analyzer /path/to/CodeAnalyzer
```

The standalone command writes `similarity-report.txt` at the workspace root and discovers
the repository's default `CodeAnalyzer.cpp` when `--code-analyzer` is omitted.

Each submission report directory includes a guided `notes.md` for TA-written
observations. Its title identifies the mapped student name and milestone when
the notes are created. Its instructional template is a collapsed info callout.
The generated `report.txt` contains automated findings and
evidence, including file-header, configured-method, and method-documentation details, GTest/extra-credit
configuration status, and output-check status. Full build and runtime output
remain available in the linked log files.
Manual notes should go in `notes.md`, while structured corrections belong in
`overrides.json`.

Console output and reports show the absolute workspace path once as a path
prefix; paths inside the workspace are then displayed as `<workspace-path>/...`.

Use the explicit reporting command for new invocations. Without a milestone,
it presents the available milestone configurations as a keyboard-navigable
selection prompt:

```bash
python3 main.py report
```

For scripted runs, provide the milestone directly:

```bash
python3 main.py report milestone2-hugh
```

The older `python3 main.py milestone2-hugh --report` form remains supported for
existing scripts and behaves the same way. The explicit command is the intended
place to add workspace-native reporting as that workflow replaces the legacy
repository reporter.

### To run all tests:
```bash
python -m tests.<type_of_test>.run  # General
python -m tests.unit.run    # Specific example
```

### To run specific tests:
```bash
python -m tests.<type_of_test>.<test_name>  # General
python -m tests.unit.shell_unit # Specific example
```

## Organization
* `root`
  * `main.py` - Main entry point.
  * `main.ps1` - Bootstrapping for Windows setup.
  * `config.py` - Reads in Grade Checker's configuration file and handles
                  different grading configurations.
  * `core`
    * `build.py` - Cross platform CXX project auto-building.
    * `shell.py` - Cross platform shell. Most notably, handles git bash on
                   Windows to call bash scripts.
    * `file_processor.py` - Iterator for different file collections.
    * `grader.py` - Main driver for Grade Checker; handles "grading".
    * `reporter2.py` - Aggregates build and grading results and writes reports.
    * `new_fetch.py` - Incomplete alternative fetcher retained for experiments.
  * `tools`
    * `util.py` - Global utility functions.
  * `scripts` - Bash scripts for things that can be done easier with UNIX shell.
    * `check-ec.sh` - Check for extra credit, specified by the following
                      parameters: `--smart_ptrs`, `--templates`, or `--gtest`.
    * `check-static.sh` - Check for static or globals.
    * `check-stl.sh` - Check for usage of the CXX STL.
    * `check-for.sh` - Checks for provided arguments.
    * `find_hpp.sh` - Search for `.hpp` files of a class, accounting for
                      different file naming conventions.
    * `find_cpp.sh` - Search for `.cpp` files of a class, accounting for
                      different file naming conventions.
  * `milestones` - JSON configuration files Grade Checker parses in for each
                   milestone's configuration.
  * `_milestoneX` - Each milestone's configuration file.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the component diagram, command flow,
configuration model, file layout, and current implementation boundaries.

See [docs/GRADING_WORKFLOW.md](docs/GRADING_WORKFLOW.md) for the grading
context, TA workflow, application requirements, edge cases, and open design
decisions.

## TODO
 * m3 onwards has a master _milestoneX.json schema change to allow for multiple
   files. refactor previous milestones to use new multiple file schema
 * decide on a cmake (current that floats around is stable), and stick to it.
   should be distributed with student files. target platform is windows w/
   visual studio, so cmake is unsupported. HOWEVER, grade_checker is run on
   *nix, so baking the *nix cmake file with the student files, then using that
   should be what's done
