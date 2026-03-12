# Change: Ruff and Radon Tool Runners for the code-review bundle

## Why

The `specfact-code-review` bundle currently exposes review findings and scoring models,
but it does not yet provide internal runners that can execute static-analysis tools and
translate their output into `ReviewFinding` records.

The upstream `specfact-cli` OpenSpec change `code-review-02-ruff-radon-runners`
defines that missing behavior. This repository needs the corresponding bundle-side
implementation so the package can ship the same review primitives.

## What Changes

- **NEW**: `specfact_code_review.tools.ruff_runner` for `ruff check --output-format json`
  parsing and `ReviewFinding` mapping
- **NEW**: `specfact_code_review.tools.radon_runner` for `radon cc -j` parsing and
  complexity-based `ReviewFinding` mapping
- **NEW**: unit tests covering category/severity mapping, file scoping, fixable
  detection, and tool-error behavior
- **NEW**: bundle documentation describing the runner behavior and thresholds

## Impact

- No breaking public command changes
- Keeps the bundle aligned with upstream `specfact-cli` OpenSpec scope
- Module signing and publish-time artifact updates are intentionally deferred to a
  follow-up step per user instruction
