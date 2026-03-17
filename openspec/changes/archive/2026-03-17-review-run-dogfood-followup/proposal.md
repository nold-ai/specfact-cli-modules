## Why

The merged `code-review-08-review-run-integration` change proved the command
surface with fixtures, but it did not yet validate `specfact code review run`
against this repository's real code. The next step is to dogfood the command on
the modules repo itself, capture any runtime gaps, and tighten the bundle until
the command behaves coherently on representative in-repo sources.

## What Changes

- Run `specfact code review run` against representative files in this
  repository instead of only synthetic fixtures
- Add a regression test for any real-world failure uncovered during dogfooding
- Fix the `specfact-code-review` bundle so repo dogfooding produces a governed
  `ReviewReport` instead of a CLI or tool integration failure
- Align the `--json` command contract with repo output conventions by routing
  JSON review output to a file path instead of stdout
- Add a repo-local developer helper for wiring live module sources into a
  workspace `.specfact/modules` shadow root for runtime validation
- Make review noise from known low-signal findings configurable so self-review
  can stay usable by default while still allowing strict/full output
- Add an interactive prompt for whether test files should be included in review
  scope, and mirror that decision point in the bundled code-review skill
- Show live progress during long-running review execution so users can see which
  step is currently running and tell that the CLI is still active
- Include untracked Python files in auto-detected review scope so newly created
  AI-generated code is not invisible to review
- Record failing and passing evidence from the real repo run

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `review-run-command`: add real-repository dogfooding coverage and any runtime
  fixups required for stable execution in this repo

## Impact

- Affected: `packages/specfact-code-review/src/specfact_code_review/run/`,
  targeted tests under `tests/unit/specfact_code_review/` and/or
  `tests/e2e/specfact_code_review/`
- User-facing: `specfact code review run` should work cleanly against actual
  modules-repo Python sources, not just synthetic review fixtures
