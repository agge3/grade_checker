# Grade Checker Project Instructions

## Project context

This repository contains a Python command-line grader for C++ code
submissions. The main workflow is coordinated by `main.py` and uses the modules
under `core/`, shared helpers under `tools/`, shell utilities under `scripts/`,
and milestone configuration files under `milestones/`.

## Before making changes

- Inspect the relevant source, configuration, tests, and call sites first.
- Preserve existing user changes and avoid modifying unrelated files.
- Treat `main.py`, `config.py`, `core/`, `tools/`, `scripts/`, and
  `ARCHITECTURE.md` as the active project areas.
- Treat `old/`, `grader_v.py`, and clearly marked prototypes as legacy unless
  the task explicitly targets them.

## Python conventions

- Use 4-space indentation and readable snake_case names.
- Prefer `pathlib.Path` for new filesystem path handling.
- Use Python typing whenever practical, including type hints for function
  parameters, return values, attributes, and important local data structures.
- Prefer precise types such as `list[str]`, `dict[str, int]`, unions, enums,
  `TypedDict`, `Protocol`, and type aliases over vague types.
- Avoid `Any` unless the value is genuinely unknowable or dynamically shaped;
  document why it is necessary when used.
- Keep type annotations consistent with the project’s supported Python version.
- Add a Sphinx-style docstring to every function you create, including private
  helper functions.
- Each new function docstring must explain, in code-agnostic terms, what the
  function is intended to accomplish and how it should be used.
- Each new function docstring must document every parameter with `:param
  name:`, including expected meaning and relevant constraints.
- Document the result with `:return:` when the function returns a value, and
  document expected failures with `:raises:` when applicable.
- Keep docstrings focused on behavior, inputs, outputs, and usage rather than
  narrating implementation details line by line.
- Add docstrings to new public classes when practical.
- Prefer small, focused functions over expanding monolithic workflows.
- Do not introduce global mutable state when a passed configuration object will
  work.
- Use context managers for files and other resources.
- Do not silently ignore invalid input; raise a useful exception or report a
  clear warning.

## Shell conventions

- Quote paths and user/configuration-derived values.
- Use arrays for command arguments rather than unsafe string concatenation.
- Check the exit status of build, copy, fetch, and grading commands.
- Avoid destructive commands unless they are explicitly required and their
  target is validated.
- Make scripts work from any working directory by resolving paths relative to
  the script or repository root where appropriate.

## Grader-specific rules

- Keep `Build`, `Grader`, `Fetcher`, and `Reporter2` constructor signatures and
  call sites consistent.
- Keep the milestone JSON schema documented when it changes.
- Do not award points based only on substring matches when a more precise check
  is practical.
- Ensure missing files, failed builds, disabled checks, and empty submissions
  have explicit behavior.
- Keep scoring separate from report formatting.
- Make report paths consistent with the repository input layout.

## Documentation conventions

- Keep architecture documentation in `ARCHITECTURE.md`.
- Keep user-facing setup and usage instructions in `README.md`.
- Use Markdown headings with a blank line before their content.
- Prefer concise explanations, diagrams, and examples where they clarify the
  workflow.
- Document known limitations with a clear explanation rather than leaving only
  ambiguous comments such as `xxx` or `TODO`.
- 

## Testing and verification

- Run the relevant unit tests after code changes.
- Run `python3 -m py_compile` or an equivalent syntax check for changed Python
  files.
- Run `git diff --check` before finishing.
- Report tests that could not run, including missing dependencies or known
  legacy test/API mismatches.
- Do not claim a fix is verified if only static inspection was performed.

## Change discipline

- Make the smallest change that satisfies the request.
- Do not rewrite working code solely for stylistic reasons.
- When documenting a bug without fixing it, use a nearby `BUG:` comment that
  explains the actual failure and affected behavior.
- Summarize changed files and verification results in the final response.
