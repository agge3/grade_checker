# Grade Checker

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
student-canvas-submissions ZIP, the required student filename, and optional
files. `README.md` is the default optional file.

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
  --required-file milestone2.cpp
```

The importer is also available from Python as
`core.submission_importer.SubmissionImporter`. It preserves the input ZIP under
`raw/`, creates normalized directories under `submissions/`, and writes
`submission_metadata.json`. Submitted ZIPs are recovered only when the required
file is unambiguous at the submitted ZIP root; extra and nested files are
reported as warnings.

When Canvas exports multiple files submitted by the same student, the importer
groups files with the same Canvas-generated metadata prefix into one normalized
submission workspace. The required file and allowed optional files are copied
there; other files are retained in the source metadata and reported as
warnings.

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
workspace at report time, and writes per-submission reports plus
`reports/summary.md`. The summary is a Markdown table containing submission,
build, and runtime statuses plus method and required-file counts. For scripted
runs, provide the workspace directly:

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

Each submission report directory includes a guided `notes.md` for TA-written
observations. The generated `report.txt` contains automated findings and
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
