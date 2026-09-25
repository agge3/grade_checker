# Grade Checker Architecture

The application is organized as a command-line orchestration layer around
repository fetching, source inspection, building, grading, and reporting.

In the application, a milestone corresponds to the Canvas assignment being
graded. “Milestone” is retained in configuration names, command-line
arguments, and paths as an implementation term for an assignment.

## Main components

```text
main.py
  |
  +-- config.py ---------------- loads and validates milestone JSON into a
  |                              typed Config object
  |
  +-- core.fetch.Fetcher ------- finds GitHub repositories and clones them
  |
  +-- core.workspace ----------- creates empty grading workspace layouts and
  |                                records workspace configuration
  |
  +-- core.submission_importer -- preserves student-canvas-submissions and normalizes
                                   submissions into isolated workspaces
  +-- core.teacher_importer ---- preserves the teacher ZIP and extracts the
                                  selected template and grading references
  |
  +-- core.build.Build --------- copies support files, configures CMake,
  |                              builds, and runs each submission
  |
  +-- core.grader.Grader ------- locates C++ files and performs source checks
  |       |
  |       +-- FileProcessor ----- normalizes file collections and opens files
  |       +-- tools.util -------- shared path, naming, and formatting helpers
  |
  +-- core.reporter2.Reporter2 -- aggregates build/grading results and writes
                                  text reports
```

## Command flow

The required command-line argument identifies a milestone configuration. For
example, `milestone2-hugh` is converted to `milestone2` for grading paths, and
`config.load_config("milestone2-hugh")` loads
`milestones/_milestone2-hugh.json`.

The interactive `create-workspace` command initializes an empty grading
workspace below the application root's `grading-workspaces/` directory. It
creates `raw/`, `students/`, `build-workspaces/`, `runs/`, and
`references/`, then records the selected milestone and directory mapping in
`workspace.json`. Student-canvas-submissions import and normalization are separate
operations handled later by `core.submission_importer`.

The `import-student-canvas-submissions` command requires an initialized
workspace, then uses `SubmissionImporter` to place the raw
student-canvas-submissions under `raw/` and
normalized student records under `students/`. Each student record stores
source files under `src-files/`, UML artifacts under `uml-diagrams/`, and
provenance plus manual-review warnings in metadata at its root. Structured
submission rules are optional milestone configuration under
`submission.required_files` and `submission.optional_files`; the legacy
`files` setting remains reserved for instructor/template files.

When reporting runs, `WorkspaceReporter` creates an isolated
`build-workspaces/{identifier}/` directory. It copies the imported teacher
template there first, then overlays the student files so matching template
files are replaced by the student's version. Submission metadata records both
file sources and any replacements.

The `import-teacher-zip` command requires an initialized workspace and the
exact member name of the nested student-template ZIP. `TeacherImporter` copies
the outer archive to `raw/`, extracts non-template artifacts under
`references/teacher/`, extracts the template under `references/template/`, and
records provenance in `references/teacher_metadata.json`. Unsafe archive paths
are rejected and `.grader-ignore` template files are skipped.

Reporting is exposed through the explicit `report` command. With no workspace
argument it offers initialized workspaces through a keyboard-navigable
selection prompt. `WorkspaceReporter` prepares each submission's build
workspace at report time, overlays student files on the teacher template, and
writes per-submission reports directly under `students/{identifier}/`. The
cumulative Markdown workspace summary is written to `summary.md` at the
workspace root. Each invocation also writes a Markdown snapshot containing
only the submissions processed by that invocation under `runs/`. The
report command can process all submissions or one or more normalized submission
identifiers. Each
submission report retains the legacy report sections (file headers, configured
methods, GTest/extra-credit status, and output-check status) while linking to
the separate build and runtime logs. It clearly marks checks that are not executed by the
workspace workflow. The
legacy `<milestone> --report` flag remains a compatibility path for repository
reporting and does not use the workspace workflow.

Each generated `students/<submission>/` directory contains the student's
`src-files/`, metadata, report, logs, notes, and overrides.

Runtime stdout is compared with the first TA-provided output reference under
`references/teacher/`. The result is recorded as an exact match, a
blank-line-only difference, or a manual-review difference in each summary,
along with the count of differing non-empty lines.
Case-only, whitespace-only, and combined case/whitespace differences are
accepted and identified separately.

The `generate-index-report` command calls
`core.report_index.create_report_index()` to
create relative symlinks under `<workspace>/report-index` for each
`students/<submission>/report.txt`, plus the workspace summary and similarity
report when present. Existing symlinks are refreshed; real files are never
overwritten.

The general `generate-index` command accepts a filepath relative to each
submission report directory and creates a relative symlink for each existing
match under `<workspace>/<filename>-index`. Required student files are resolved from the
matching student's `src-files/` directory. The interactive command offers the
standard report files and required files recorded in submission metadata.
The `generate-index-runtime-log` and `generate-index-buildtime-log` commands
remain shortcuts for the two log filenames, using
`<workspace>/runtime-output.log-index` and `<workspace>/build-output.log-index`.

`load_config()` validates the JSON and returns a `Config` object. `Config`
implements the mapping interface, so existing consumers can use expressions
such as `cfg["options"]["build"]`. The typed `cfg.data` property exposes the
declared `ConfigData` structure, which is composed of `TypedDict` definitions
for options, grading settings, fetching settings, extra credit, and method
definitions.

Configuration is passed explicitly to application components. `Fetcher`,
`Build`, `Grader`, and `Reporter2` receive the configuration they need instead
of reading a mutable module-level `_config` variable. This makes separate
configuration instances possible and keeps configuration state visible in the
call graph.

The supported flags are independent and may be combined:

1. `--fetch` creates or clears the configured repository directory, finds
   matching organization repositories through the GitHub API, filters them by
   username and date, and clones them.
2. `--grade` creates a `Grader`, optionally builds each target, and is intended
   to run source checks. In the current implementation, most grading calls in
   `main.py` are commented out, so this path primarily performs a build.
3. `--report` creates `Reporter2`, processes repositories, optionally copies
   instructor files, builds and runs submissions, parses milestone-specific
   output, performs source checks, and writes one text report per repository.

The explicit workspace reporting command also accepts `--code-analyzer`. It
compiles and runs the unchanged instructor `CodeAnalyzer.cpp` from a temporary
staging directory, supplying its hard-coded JSON filename with a temporary
source-only `inputRoot` containing one directory per student. The source index
contains only C/C++ files from each student's `src-files/`; metadata, reports,
templates, and build output are excluded. The resulting report is preserved
under `similarity-report.txt` at the workspace root.
Without an explicit path, the reporter checks the repository root for an
optional `CodeAnalyzer/CodeAnalyzer.cpp` or `CodeAnalyzer.cpp`; absence of both
leaves similarity analysis marked as not run.

The standalone `analyze-similarity` command runs `core.similarity.SimilarityAnalyzer`
against the temporary source-only index derived from `students/` and writes
`similarity-report.txt`
without rebuilding submissions or rewriting the grading summary.

## Configuration model

`core.workspace.create_workspace()` owns workspace initialization and writes
the workspace-level `workspace.json` metadata. `SubmissionImporter` is a
separate later-stage component: it preserves student-canvas-submissions under
`raw/`, creates normalized directories under `students/`, and records
provenance and warnings in `submission_metadata.json`. Structured student ZIPs
are validated as one top-level project directory; source files and directly
contained UML matches are imported separately, while invalid layouts remain
available for manual review.

Milestone JSON files provide the application’s dependency-injection data. The
loader maps their contents to the typed `ConfigData` structure:

- `prof`, `org`, `glob`, and `clone` control repository discovery.
- `classes` and `methods` describe the C++ interfaces expected from students.
- `options` controls copying, building, output checking, and output display.
- `grading` provides point categories.
- `extra_credit` controls optional shell-script checks.
- `fetch` controls whether the repository destination is cleared first.
- `files` lists instructor-provided files, which `Build.copy_fhs()` can add to
  a submission.

## File and build layout

Fetched repositories are normally stored under:

```text
repos/{milestone}-{prof}/
```

Instructor support files are stored under:

```text
project_fhs/{milestone}-{prof}/
```

For Unix-like systems, `Build` creates a `build/` directory inside each
submission, runs CMake and Make, then executes the target discovered from
`CMakeLists.txt`. The `scripts/` directory contains shell helpers used for
file discovery and extra-credit checks.

## Current implementation boundaries

`main.py`, `config.py`, `core/build.py`, `core/fetch.py`,
`core/submission_importer.py`, `core/grader.py`, and `core/reporter2.py` form
the intended current application. `grader_v.py`,
`core/new_fetch.py`, `core/script_runner.py`, `core/spreadsheet.py`, and the
`old/` directory are experimental, obsolete, or incomplete implementations and
are not part of the normal `main.py` workflow.

The current codebase still contains API mismatches between `Reporter2`,
`Build`, and `Grader`, as well as incomplete scoring paths. These limitations
are documented in source comments and should be resolved before treating the
reporting workflow as production-ready.
