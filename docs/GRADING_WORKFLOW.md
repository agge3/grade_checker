# Grade Checker Grading Workflow

This document describes the grading problem the application is intended to
solve. It captures the TA's workflow, application requirements, user-facing
behavior, and design questions that should remain visible while the
implementation evolves.

`ARCHITECTURE.md` describes the software components that implement this
workflow. `README.md` describes setup and routine command usage.

## Terminology

In this application, a **milestone** is the Canvas assignment being graded.
The terms are interchangeable in the grading workflow. The implementation
currently uses `milestone` in configuration names, command-line arguments, and
paths, so that internal terminology may appear in addition to “assignment.”

## Purpose and users

The Grade Checker assists a teaching assistant (TA) with evaluating C++
project submissions. It automates repeatable checks and gathers evidence, but
the TA remains responsible for reviewing results and entering grades in the
instructor's spreadsheet.

Students receive a project template containing some instructor-provided code.
They are expected to submit the files they created or changed through Canvas.
Because submissions may be incomplete, incorrectly structured, or otherwise
unreliable, the application must treat every student-canvas-submissions item as untrusted
input and report problems clearly.

The TA has the following teacher-only materials:

- A student-canvas-submissions ZIP exported from Canvas.
- A teacher ZIP archive containing the grading spreadsheet, solution source
  files, an expected program-output log, and a ZIP of the student project
  template.
- The instructor-provided `CodeAnalyzer` package for comparing submission
  source-code similarities. This package must not be modified by the Grade
  Checker.

The TA must tell the application which file inside the teacher ZIP is the ZIP
containing the student project template. The other teacher-archive artifacts
are grading references: the spreadsheet is the final manual grading record,
the solution source files are a known-correct implementation for the TA's
manual reference, and the expected output log supports program-output checks.
The `CodeAnalyzer` package is used only for similarity analysis, and its output
is informational evidence for the TA.

## Canvas submission-export assumptions

Canvas's instructor **Download Submissions** workflow produces one ZIP for an
assignment. The extracted student-canvas-submissions ZIP contains a `submissions` folder containing
the downloaded work. For individual assignments, Canvas adds the student's
name to downloaded filenames in last-name-first form; for group assignments,
it uses the group name. Anonymous grading removes student names from those
downloaded filenames.

The bulk ZIP should therefore be treated as a source of submission files, not
as a student roster or complete metadata export. The grader does not identify
the student who made a submission. The TA is responsible for manually
inferring the student from the downloaded filename when transferring results
to the spreadsheet. The report only needs to reproduce that original filename;
if the TA needs to inspect the submission again, they can locate it in the
original Canvas export.

The normal ZIP should not be expected to provide a dependable Canvas user ID,
submission timestamp, attempt history, due-date status, or complete roster.
Canvas documents that only the most recent submission is included, and that
students with concluded enrollments are omitted. Bulk download also has
submission-type limitations: it supports file uploads, text entries, website
URLs, and Google Docs submissions, but not media recordings or embedded media
within text entries.

Consequences for the grader:

- Discover submissions from the student-canvas-submissions contents, including the usual
  `submissions` wrapper, while allowing for minor layout variation.
- Include the original Canvas submission filename prominently in the report.
- Preserve original relative paths as submission labels and audit information,
  without treating filenames as verified student identities.
- Warn the TA that a bulk ZIP represents the latest available attempt only.
- Make anonymous or group assignments explicit configuration choices rather
  than inferring identity from filenames.

Canvas's submissions API can expose fields such as `assignment_id`, `user_id`,
`submitted_at`, `attempt`, `late`, `seconds_late`, and `workflow_state`, but API
metadata is outside the current workflow. The application should not require
API access or attempt to infer a student's identity from those fields.

Sources: [Canvas instructor guidance on downloading all student
submissions](https://community.instructure.com/en/kb/articles/660693-how-do-i-download-all-student-submissions-for-an-assignment)
and [Canvas Submissions API documentation](https://canvas.instructure.com/doc/api/submissions.html).

### Current first-milestone submission format

The first milestone currently expects one required student file. The expected
filename is defined by the reusable milestone configuration in the
`milestones/` directory. Students may also submit an optional `README.md`. The
configuration may be outdated when reused for a new assignment. For now, the
grader should assume that the configuration matches the assignment, but should
detect likely mismatches and notify the TA that the configuration file needs
review. The notification should include specific details, such as the
configured filename, files found in the teacher ZIP, and the affected
submissions. Automatic configuration changes are out of scope for this
temporary resolution. The exact student-canvas-submissions ZIP structure is not yet considered
stable, so the importer should be tolerant of wrapper folders and should
preserve the raw student-canvas-submissions for inspection.

Based on current observations, Canvas modifies the downloaded filename by
prefixing metadata before the filename supplied by the student. The observed
shape is approximately:

```text
<canvas-prefix>_[LATE]_<student-filename>[-<number>].<extension>
```

The prefix may contain the student's first and last name and numeric values
whose meaning is not currently relied upon. `[LATE]` may be absent. The
optional `-<number>` appears to distinguish repeated submissions with the same
filename. The grader should preserve the entire original filename and should
not depend on understanding or perfectly parsing the Canvas-generated prefix.
The student-supplied filename and extension are useful evidence, but the app
still evaluates the extracted submission rather than identifying the student.

For internal workspace naming, use the student's first name, last name, and
the two Canvas-generated numeric values. Exclude the optional `[LATE]` marker
and a trailing duplicate-attempt suffix such as `-2`. The full original
filename remains available in metadata and reports. If removing those markers
produces a name collision, the application must report the collision and use a
deterministic disambiguation that does not discard either submission.

Canvas's bulk export provides only the most recent submission. The grader
should not imply that it has access to earlier attempts, even when the filename
contains an attempt-like suffix.

Students may accidentally submit a ZIP containing the requested file or an
entire project instead of submitting only the requested file. For the first
milestone, the importer should:

- Detect a submitted ZIP when a direct required file is not present.
- Check the root of the submitted ZIP for the filename specified by the
  milestone configuration and the optional `README.md`.
- Extract the needed root-level file(s) into the normalized submission
  workspace when the selection is unambiguous.
- Preserve the submitted ZIP and its internal paths for audit purposes.
- Mark the submission as recovered from an archive in both the report and the
  workspace metadata.
- Flag files found below the ZIP root, ambiguous cases, and multiple plausible
  required files for TA review instead of guessing.
- Report extra files or a complete-project submission as a submission-structure
  warning, even if the required file can be recovered. Extra files are ignored
  for the normalized build and automated grading.

The importer does not need to support arbitrary nested project layouts. If a
student's source file is inside another directory, the TA can manually unzip
the student's submission and copy the source file directly into that
submission's normalized workspace. The workspace and report should make this
manual-repair path visible so the TA knows why the grading input differs from
the original archive.

## Intended TA workflow

1. The TA invokes the application's workspace-creation CLI command.
2. The application interactively prompts for the workspace directory and
   optional milestone configuration, then creates the empty workspace layout
   and writes its workspace configuration.
3. The TA later supplies the student-canvas-submissions ZIP, teacher ZIP, template,
   reference solution, expected-output log, and grading spreadsheet through the
   import/setup workflow.
4. The application validates and preserves the original inputs.
5. The application discovers individual submissions and creates an isolated,
   normalized workspace for each one. The submission's internal name is based
   on the Canvas-generated filename metadata, excluding the optional `[LATE]`
   marker and the optional duplicate-attempt suffix such as `-2`.
6. The application applies the assignment configuration and instructor-provided
   files, then runs the enabled checks.
7. The application builds and, where applicable, executes each submission with
   explicit timeout and failure behavior.
8. The application produces a report for every submission, including
   successes, failures, warnings, evidence, and checks requiring manual review.
9. The TA reviews reports, manually maps each submission to a student, resolves
   unusual cases using notes or overrides, and transfers the relevant results
   into the spreadsheet.
10. The workspace remains reproducible so the TA can rerun grading after fixing
   one submission or changing a grading rule.

The original archives and raw run results should remain separate from any
normalized files or TA adjustments. A correction should never require
editing the original submission.

## Required grading behavior

### Input and submission handling

The application should explicitly handle:

- Extra top-level folders and nested submission folders.
- Missing, empty, duplicated, or ambiguously named submissions.
- Missing required files and unexpected extra files.
- Submitted ZIP files whose expected source files are at the ZIP root.
- Nested source files or project directories that require manual TA repair.
- A first-milestone submission containing exactly one required file, with an
  optional `README.md`.
- A ZIP submitted in place of the requested file or a ZIP containing an entire
  project.
- Template files ending in `.grader-ignore`, which must not be copied.
- Build products, editor metadata, and platform-specific files.
- Student files that were provided by the template versus files the student
  was expected to create or modify.
- Duplicate or ambiguous submission filenames.
- Internal-name collisions after removing `[LATE]` and duplicate-attempt
  suffixes.
- Extra submitted files, which should be reported to the TA and ignored by the
  normalized build unless an assignment-specific criterion explicitly uses
  them.

The application should preserve the original archive, record the source name
and original filename for each submission, and assign a stable internal
submission identifier. It should not assign a student identity.

### Template and instructor-provided files

The selected student-template ZIP is the source of the grader files needed to
build submissions. Every file in that template is copied into every
submission's normalized workspace and marked as a grader-provided file. Any
file whose name ends with `.grader-ignore` is excluded from copying. This rule
applies to ignored files wherever they occur in the template archive.

The teacher ZIP itself, the grading spreadsheet, the solution source files,
and the expected-output log are not copied into student build workspaces unless
an assignment-specific check explicitly requires a separate reference input.
The existing `project_fhs` concept represents the template files that can be
made available in each student's normalized workspace.

The workspace should retain provenance for copied files so reports and later
inspection can distinguish grader files from student-submitted files. The
application should also report how many template files were copied and how
many `.grader-ignore` files were excluded.

Instructor-provided source and build-support files should be treated
separately from build output. The safe default is to give each submission its
own complete build workspace, containing the normalized student files and the
instructor files needed to compile them. A shared read-only cache of unchanged
instructor files may be an implementation optimization, but compiled objects,
executables, generated files, and logs must not be shared between submissions.
This prevents stale artifacts or one student's changes from affecting another
student's build and makes a single-submission rerun reproducible.

For the initial implementation, copying the selected template files into each
submission's normalized workspace is the simplest policy. The application
should record which files were supplied by the teacher and which came from the
submission. A single common build directory for all students is not the
default workflow. Normalization should copy grader files first, then overlay
the student's submitted file at the normalized destination path defined by the
milestone configuration. This is expected when students modify a file that
was present in the template. The workspace metadata should record that the
student file replaced a grader file.

The known-correct solution is manual reference material only. The application
does not compile it, compare student code against it, or use it in automated
grading.

### Submission similarity analysis

The application must invoke the instructor-provided `CodeAnalyzer` to compare
student submission source-code similarities. Its source files and behavior are
external inputs and must remain unchanged. The analyzer's output is evidence
for the TA, not a point calculation or automatic academic-integrity finding.

Similarity analysis must use a student-only submissions area separate from the
normalized build workspaces. A suitable workspace layout is:

```text
workspace/
  submissions/
    submission-1/
      expected-source.cpp
    submission-2/
      expected-source.cpp
  build-workspaces/
    submission-1/
      template and grader files
      student file overlaid on the template
      build/
    submission-2/
      template and grader files
      student file overlaid on the template
      build/
  reports/
    submission-1/
      report.txt
      build-output.log
      runtime-output.log
    submission-2/
      report.txt
      build-output.log
      runtime-output.log
    similarity-report.txt
```

`workspace/submissions/` is the normalized student-only view and can be passed
directly to `CodeAnalyzer` as its `inputRoot`. Each directory should contain
only source files that came from that submission, including a recovered source
file when the TA has manually repaired a submission. It must not contain copied
grader/template source files, the known-correct solution, build output, or
unrelated files. Otherwise, identical instructor files could inflate
similarity results.

The provided analyzer currently expects one directory per submission,
recursively reads C++ source extensions, compares normalized token sets, and
writes a cohort-level text report with pairwise percentages and possible-copy
flags. The Grade Checker should preserve that output as a separate similarity
report and identify which submission directories were analyzed. It should not
relabel those directories as verified students or assign points from the
similarity percentages.

The provided analyzer currently obtains its JSON configuration through a
hard-coded source-level path, while the JSON supplies its input root and output
report path. Since the analyzer must not be modified, integrating it requires
an execution/staging arrangement that satisfies that interface or a documented
TA-operated invocation. This is an implementation integration issue, not a
reason to alter the instructor-provided package.

When practical, the grader should compare a submission with the original
student template to identify missing, extra, and modified files. Byte-level
differences should not automatically be treated as meaningful when line
endings or generated artifacts explain the difference.

### Automated checks

Checks may include:

- Required file and directory presence.
- File headers and whether the header identifies the student.
- Method and class documentation.
- Required method declarations and implementations.
- Forbidden or suspicious changes to instructor-owned files.
- Static checks such as globals, STL usage, or extra-credit features.
- Build success and compiler diagnostics.
- Program execution, timeout, crash, and exit status.
- Expected output and output-format requirements.
- Original filename and archive metadata, when present; the grader does not
  claim this identifies the student or proves the Canvas submission time.

Each check should have a stable criterion identifier, an enabled/disabled
state, a result, evidence, and an indication of whether the result is
automated or requires TA judgment. A failed build should not automatically
prevent independent source or documentation checks from running.

Submission timestamps are outside the current file-only workflow. File
modification times inside an archive must not be treated as evidence of when a
student submitted. The original report filename is sufficient context for the
instructor's separate late-submission handling. The application should
preserve that filename, may display an observed `[LATE]`
marker as information, and should not calculate late penalties or infer
earlier attempts. The TA treats every submission as on time when evaluating
the assignment criteria. The instructor, not the TA or the application, is
responsible for determining any late-submission score adjustment.

### Reports and manual grading

Reports are grading aids rather than the final gradebook. The current report
format is a sectioned plain-text file with one report per submission, following
the general style of the existing report reference. A per-submission report
should provide:

- Submission identifier, original filename, and source path.
- Submission structure and file inventory warnings.
- A concise criterion-by-criterion summary.
- Evidence, including filenames and line numbers when available.
- Build and runtime diagnostics.
- A separate build-output log containing configuration, compiler, linker, and
  build-system output.
- A separate runtime-output log containing only the student's program output
  and relevant execution diagnostics.
- Checks that were skipped, disabled, or not applicable.
- A clear distinction between failure, warning, and manual review.
- A location for TA notes and overrides.

The application does not calculate points or assign grades. It provides
information and evidence for each criterion, and the TA decides the points
manually in the grading spreadsheet. Report criterion names and stable
identifiers should align with the spreadsheet so the TA can transfer findings
efficiently. The spreadsheet should remain unchanged unless the TA
intentionally updates it. These criterion points exclude any late-submission
adjustment, which is handled separately by the instructor.

The human-readable report may summarize or link to these logs, but build output
and runtime output must not be merged into one log file. Each submission's log
files should be stored with that submission's results and identified clearly
in the report. The report should remain quick to scan for manual spreadsheet
grading while retaining enough evidence for unusual cases.

The workspace uses `reports/` as the output root. Each submission has its own
directory containing `report.txt`, `build-output.log`, and
`runtime-output.log`. The cohort-level `similarity-report.txt` is stored
directly under `reports/` because it compares submissions with one another.

Each report should include the rule/configuration version used for grading and
the time the grading run occurred. Rule files should document their version
and the date or time each version changed, using comments or a comparable
annotation. If the rules change after a submission has been graded, previously
completed submissions are not regraded; the new version applies only to future
grading runs as directed by the TA.

## Exceptions, overrides, and reproducibility

Unique edge cases are expected. The TA should be able to correct or annotate
the interpretation of one submission's findings without changing the raw
submission, silently changing the assignment configuration, or forcing an
entire cohort to be graded again. Because the application does not calculate
points, an override does not change an application score; it records the TA's
review of the reported evidence for use when the TA assigns spreadsheet
points.

The design should support:

- Per-submission notes.
- Per-criterion finding corrections or annotations with an explanation.
- A record of the original automated result.
- Rerunning only one submission when possible.
- Rerunning the cohort with a new configuration version.
- Persistent logs and diagnostics for disputed results.
- Clear indication of which results came from which run and configuration.

Overrides should be visible in reports and should not be mistaken for
automated results.

## Safety and operational requirements

Student code is untrusted. Compilation and execution should be isolated as
far as practical, with bounded execution time, controlled working directories,
and resource limits appropriate to the host environment.

The application should be resilient to one malformed or malicious submission.
One student's failure should be recorded and allow the remaining submissions
to proceed. Destructive cleanup should be explicit, scoped to the grading
workspace, and preferably preceded by a dry-run or confirmation mechanism.

The workspace should make it easy to answer:

- Which input archives were used?
- Which configuration and reference solution were used?
- Which checks ran?
- What failed, and why?
- What did the TA change manually?
- Can the result be reproduced later?

## Suggested conceptual data flow

```text
Student ZIP + teacher ZIP + reference solution + rubric configuration
                              │
                              ▼
                 Project import and validation
                              │
                              ▼
             Submission discovery and normalization
                              │
                              ▼
       Isolated per-submission build and grading workspaces
                              │
                              ▼
                  Structured criterion results
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        Submission reports             TA notes/overrides
                 │                         │
                 └────────────┬────────────┘
                              ▼
                 Manual spreadsheet completion
```

## Open design decisions

These decisions should be resolved before the workflow is treated as
production-ready:

1. **Milestone 2 design issue:** whether the current root-level-only ZIP rule
   should be expanded, and which additional layouts would justify that
   complexity. For milestone 1, root-level-only extraction remains the active
   rule and deeper layouts use the TA's manual-repair workflow.
2. **Build-workspace design:** the current behavior is to copy every selected
   template file except files ending in `.grader-ignore` into each submission
   workspace and mark those files as grader files. Build output remains
   per-submission; future shared read-only caching is only an optimization.
3. How should modified template files and omitted expected files affect
   grading? Extra files are reported and ignored by the current workflow.
4. **Milestone 2 design issue:** what execution isolation, timeout, and
   resource limits are acceptable on the TA's machine? For milestone 1, the
   baseline is separate per-submission workspaces and explicit handling so a
   failed or hanging submission does not prevent the remaining submissions
   from being processed.
5. What kinds of per-submission finding corrections or annotations are allowed,
   and how must they be documented? The application does not assign points;
   the TA records points manually in the spreadsheet.

## Application requirements checklist for future changes

When proposing or implementing a feature, review whether it affects any of
the following application and grading requirements:

- The TA can import and understand the required input artifacts.
- Reused configuration is assumed to match, but likely mismatches produce a
  clear TA notification with supporting details.
- The application evaluates submissions without needing to know student
  identities.
- The application reports findings and evidence but does not calculate points
  or assign grades.
- The provided `CodeAnalyzer` runs unchanged against student-submitted source
  files only, and its similarity report is presented as TA evidence.
- The TA evaluates every submission as on time; the instructor handles any
  late-submission score adjustment separately.
- Reports reproduce the original Canvas submission filename so the TA can
  locate the artifact in the original export.
- Original inputs remain preserved and traceable.
- Malformed submissions receive explicit, useful outcomes.
- Independent checks can still provide value when builds fail.
- Student code cannot disrupt grading of other students.
- Reports provide evidence usable for manual spreadsheet grading.
- A unique student edge case can be corrected locally and audibly.
- Results can be reproduced from recorded inputs and configuration.
- Reports include the rule version and grading time, and rule files document
  when versions changed.
- Documentation remains clear about what is automated versus manual.

If a future prompt proposes a feature that conflicts with or leaves one of
these requirements ambiguous, the design discussion should call that out
before implementation begins.
