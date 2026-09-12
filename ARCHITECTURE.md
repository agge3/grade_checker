# Grade Checker Architecture

The application is organized as a command-line orchestration layer around
repository fetching, source inspection, building, grading, and reporting.

## Main components

```text
main.py
  |
  +-- config.py ---------------- loads and validates milestone JSON into a
  |                              typed Config object
  |
  +-- core.fetch.Fetcher ------- finds GitHub repositories and clones them
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

## Configuration model

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

`main.py`, `config.py`, `core/build.py`, `core/fetch.py`, `core/grader.py`,
and `core/reporter2.py` form the intended current application. `grader_v.py`,
`core/new_fetch.py`, `core/script_runner.py`, `core/spreadsheet.py`, and the
`old/` directory are experimental, obsolete, or incomplete implementations and
are not part of the normal `main.py` workflow.

The current codebase still contains API mismatches between `Reporter2`,
`Build`, and `Grader`, as well as incomplete scoring paths. These limitations
are documented in source comments and should be resolved before treating the
reporting workflow as production-ready.
