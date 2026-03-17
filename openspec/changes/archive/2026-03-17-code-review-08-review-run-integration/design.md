# Design: code-review run integration for modules repo

## Scope

This reapplication is intentionally limited to bundle-owned assets in
`specfact-cli-modules`:

- `packages/specfact-code-review/src/specfact_code_review/run/*`
- review fixtures and tests under `tests/`
- command contract YAML under `tests/cli-contracts/`
- bundle docs and release metadata

Core CLI plumbing is already provided by the sibling `specfact-cli` dependency
installed through the local Hatch bootstrap.

## Command behavior

`specfact code review run` should support:

- positional file arguments
- `--json` for `ReviewReport` JSON
- `--score-only` for the integer `reward_delta`
- `--fix` to run `ruff check --fix` and then re-run the review
- `--no-tests` to skip the TDD gate
- default file discovery from `git diff HEAD --name-only`

Human-readable output should group findings by category and include the
governed verdict, CI exit code, score, and reward delta.

## Test strategy

- Add deterministic clean/dirty fixtures inside `tests/fixtures/review/`
- Cover command behavior with Typer tests
- Add an end-to-end runtime test that executes the installed `specfact` command
- Validate scenario YAML presence and shape with a repo-local schema check
- Record both failing-first and passing evidence in `TDD_EVIDENCE.md`
