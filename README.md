# Grade Checker

## Usage
### Setup:
#### python
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

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

The submission archive importer is available as
`core.submission_importer.SubmissionImporter`. Give it the Canvas ZIP, an
output directory, and the milestone's required filename. It preserves the raw
ZIP and creates normalized workspaces under `submissions/`, with provenance in
`submission_metadata.json`.

### Create a grading workspace

Initialize an empty grading workspace interactively:

```bash
python3 main.py create-workspace
```

The command prompts for a workspace name and optional milestone
configuration. Workspaces are created under the application root's
`grading-workspaces/` directory. `--output` and `--milestone` may be supplied
to skip those prompts. Each workspace contains `raw/`, `submissions/`,
`build-workspaces/`, `reports/`, and `references/`, plus `workspace.json`.
Submission archive importing is a separate future workflow.

For example:

```text
$ python3 main.py create-workspace
Workspace name [grading-workspace]: milestone2
Milestone configuration (optional): milestone2-hugh
Created grading workspace: .../grading-workspaces/milestone2
Workspace configuration: .../grading-workspaces/milestone2/workspace.json
Milestone: milestone2-hugh
```

This creates the following workspace below the repository root:

```text
grading-workspaces/
└── milestone2/
    ├── build-workspaces/
    ├── raw/
    ├── references/
    ├── reports/
    ├── submissions/
    └── workspace.json
```

The milestone prompt may be left blank when the workspace is not yet tied to a
specific grading configuration. To provide values without prompts:

```bash
python3 main.py create-workspace \
  --output grading-workspaces/milestone2 \
  --milestone milestone2-hugh
```

## TODO
 * m3 onwards has a master _milestoneX.json schema change to allow for multiple
   files. refactor previous milestones to use new multiple file schema
 * decide on a cmake (current that floats around is stable), and stick to it.
   should be distributed with student files. target platform is windows w/
   visual studio, so cmake is unsupported. HOWEVER, grade_checker is run on
   *nix, so baking the *nix cmake file with the student files, then using that
   should be what's done
