# Changelog

All notable changes to Grade Checker are documented here. Commit references
are included so each summarized entry can be traced back to the repository
history.

Version boundaries:

- v2.0 begins at `ce5e296`.
- v2.1 begins at `5905f9d`.
- v2.2 begins at `2c315bd`.

## [Unreleased]

Changes for the next release are recorded here as work is completed. The AI
maintainer must not move these entries into a numbered release or change
`VERSION` without asking for approval.

### Added

- Added an AI-managed versioning workflow with approval-gated releases.

### Changed

- Updated workspace and project documentation for ongoing version tracking.

### Fixed

### Deprecated

### Removed

### Breaking

## [2.2.0] - 2026-10-13

### Added

- Added student names to TA notes and highlighted the supplied template in
  reports (`31ab6d1`).
- Added directory targets and multi-file support to the report index generator
  (`c87d662`, `bb6d5b6`).
- Added support for importing all submissions or selecting individual
  submissions (`31c5d1b`).

### Changed

- Updated Milestone 2 configuration files (`ac971ce`).
- Updated external student identifier mappings (`ea0e6a5`).

### Fixed

- Fixed reporter method-header discovery (`2c315bd`).

## [2.1.0] - 2026-09-28

### Added

- Added runtime-output comparison flags for case and whitespace differences
  (`5905f9d`).
- Added structured Milestone 2 submission and UML importing (`fae7f9f`).
- Added import summaries for student submissions (`4570c57`).
- Added human-readable student identifier mappings (`1a59ecc`).
- Added mapped-name and extension options for generated report indexes
  (`e06a15e`).

### Changed

- Unified student submissions and reports in the workspace model (`6161328`).
- Improved handling of multi-file submissions (`6417bc4`).
- Renamed the legacy summary output to `report-summary.md` (`e221f5b`).
- Improved report command-line output and summary formatting
  (`21c58d4`, `47bf43f`).
- Improved method search behavior (`4b55509`).

## [2.0.0] - 2026-09-14

### Added

- Redesigned the milestone configuration system (`ce5e296`).
- Added the grading workflow design and documented decisions for submission
  layouts, teacher files, extra files, reports, manual review, late work, and
  changing grading rules (`199ec2e`, `9cd181f`, `02ded90`, `89b2b5e`,
  `c545b70`, `89f689c`, `fcc641a`, `78165ae`).
- Added the code-analyzer design and integrated code-analyzer support into the
  grading workflow (`6f95a0c`, `f42aba0`).
- Added grading workspace creation and a submission importer with interactive
  and command-line workflows (`5a355a0`, `f395766`, `59a9f85`, `705efa2`,
  `501d32d`, `4e5e7dc`, `9b586de`).
- Added copyable commands after interactive operations (`c60cb05`).
- Added teacher archive and template importing plus workspace reporting
  (`f879944`, `1284bac`, `6240d2b`, `3e8f1fd`, `de9a02b`).
- Added report formatting, single-submission reporting, and improved path
  display (`735809d`, `7cd04f7`, `ed2a684`, `c41a5cf`, `130e928`).
- Added report indexes, interactive index generation, generic file indexing,
  and submission report links (`9e339c5`, `43e9af9`, `9319a8d`, `66f0b40`).
- Added runtime output diffing and cumulative report summaries (`8041fbd`,
  `c28b265`).

### Changed

- Improved report messages for student ZIP submissions (`aee5668`).
- Improved method and file-header formatting, report summaries, Markdown
  output, and console output (`3b46862`, `1c32460`, `bcfbb40`, `f0b45ac`,
  `24741a7`).
- Updated architecture and project-agent documentation (`31bf772`, `da30b29`).

### Fixed

- Fixed importing submission files with numeric filename suffixes (`3a24849`).

### Removed

- Excluded generated code-analyzer files from version control (`68dc022`).
