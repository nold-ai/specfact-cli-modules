# TDD evidence — docs-15-code-review-validation-guardrails

## Docs validation (script + unit tests)

- `python scripts/check-docs-commands.py` — passing (no findings) after link and front matter fixes.
- `python scripts/check-docs-commands.py --jekyll-bundle-check` — passing locally after `public_suffix` lockfile regression to 6.0.2 (`cd docs && bundle check`).
- `python -m pytest tests/unit/docs/test_docs_review.py tests/unit/docs/test_code_review_docs_parity.py tests/unit/test_check_docs_commands_script.py tests/unit/test_pre_commit_quality_parity.py -q` — passing.

## OpenSpec

- `openspec validate docs-15-code-review-validation-guardrails --strict` — passing.

## Format / lint

- `hatch run format` and `hatch run lint` — passing for touched Python.

## SpecFact code review

- `hatch run specfact code review run --json --out .specfact/code-review.json --scope changed` — passing (2026-04-15); evidence at `.specfact/code-review.json`.
