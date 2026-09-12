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
unreliable, the application must treat every student archive as untrusted
input and report problems clearly.

The TA has the following teacher-only materials:

- A ZIP archive containing all student submissions exported from Canvas.
- A teacher ZIP archive containing the project template and instructor-provided
  files.
- An instructor spreadsheet used as the final grading record.
- One known-correct implementation of the assignment.

## Canvas submission-export assumptions

Canvas's instructor **Download Submissions** workflow produces one ZIP for an
assignment. The extracted archive contains a `submissions` folder containing
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

- Discover submissions from the archive contents, including the usual
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

## Intended TA workflow

1. The TA creates a grading workspace for the Canvas assignment (called a
   milestone by the current implementation).
2. The TA imports the student-submission ZIP and teacher ZIP, and associates
   the reference solution and grading spreadsheet with the workspace.
3. The application validates and preserves the original inputs.
4. The application discovers individual submissions and creates an isolated,
   normalized workspace for each one.
5. The application applies the assignment configuration and instructor-provided
   files, then runs the enabled checks.
6. The application builds and, where applicable, executes each submission with
   explicit timeout and failure behavior.
7. The application produces a report for every submission, including
   successes, failures, warnings, evidence, and checks requiring manual review.
8. The TA reviews reports, manually maps each submission to a student, resolves
   unusual cases using notes or overrides, and transfers the relevant results
   into the spreadsheet.
9. The workspace remains reproducible so the TA can rerun grading after fixing
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
- Nested ZIP files and non-source artifacts.
- Build products, editor metadata, and platform-specific files.
- Student files that were provided by the template versus files the student
  was expected to create or modify.
- Duplicate or ambiguous submission filenames.

The application should preserve the original archive, record the source name
and original filename for each submission, and assign a stable internal
submission identifier. It should not assign a student identity.

### Template and instructor-provided files

The teacher ZIP is assignment input and must have an explicit file policy.
Each relevant file should be classified as required, instructor-provided,
student-modifiable, forbidden to modify, optional, or ignored.

The existing `project_fhs` concept represents instructor-provided files that
can be made available in a student's normalized workspace. The workflow must
make clear whether such files are copied before building, included only for
comparison, or excluded from grading.

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
student submitted.

### Reports and manual grading

Reports are grading aids rather than the final gradebook. A per-submission report
should provide:

- Submission identifier, original filename, and source path.
- Submission structure and file inventory warnings.
- A concise criterion-by-criterion summary.
- Evidence, including filenames and line numbers when available.
- Build and runtime diagnostics.
- Checks that were skipped, disabled, or not applicable.
- A clear distinction between failure, warning, and manual review.
- A location for TA notes and overrides.

Scoring should be stored separately from report formatting. The spreadsheet
should remain unchanged unless the TA intentionally updates it. Report
criterion names and stable identifiers should align with the spreadsheet so
results can be transcribed efficiently.

## Exceptions, overrides, and reproducibility

Unique edge cases are expected. The TA should be able to correct the grading
of one submission without changing the raw submission, silently changing the
assignment configuration, or forcing an entire cohort to be graded again.

The design should support:

- Per-submission notes.
- Per-criterion overrides with an explanation.
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

1. What exact archive layouts should be accepted automatically, and which
   should require TA intervention?
2. Which files from the teacher ZIP are copied into each submission, and which
   are used only for comparison or testing?
3. How should modified template files, omitted files, and extra files affect
   grading?
4. What execution isolation, timeout, and resource limits are acceptable on
   the TA's machine?
5. Should the known-correct solution be used for output comparison, tests,
   structural comparison, or all three?
6. What report format is fastest for the TA to use alongside the spreadsheet?
7. What kinds of per-submission overrides are allowed, and how must they be
   documented?
8. If late submissions, resubmissions, or multiple Canvas exports matter,
   what separate TA process will supply that information to the spreadsheet?
9. How are rubric changes versioned after grading has begun?

## Application requirements checklist for future changes

When proposing or implementing a feature, review whether it affects any of
the following application and grading requirements:

- The TA can import and understand the required input artifacts.
- The application evaluates submissions without needing to know student
  identities.
- Reports reproduce the original Canvas submission filename so the TA can
  locate the artifact in the original export.
- Original inputs remain preserved and traceable.
- Malformed submissions receive explicit, useful outcomes.
- Independent checks can still provide value when builds fail.
- Student code cannot disrupt grading of other students.
- Reports provide evidence usable for manual spreadsheet grading.
- A unique student edge case can be corrected locally and audibly.
- Results can be reproduced from recorded inputs and configuration.
- Documentation remains clear about what is automated versus manual.

If a future prompt proposes a feature that conflicts with or leaves one of
these requirements ambiguous, the design discussion should call that out
before implementation begins.
