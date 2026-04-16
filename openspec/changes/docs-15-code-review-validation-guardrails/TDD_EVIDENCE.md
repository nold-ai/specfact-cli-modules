# TDD evidence — docs-15-code-review-validation-guardrails

## Docs validation (script + unit tests)

- `python scripts/check-docs-commands.py` — passing (no findings) after link and front matter fixes.
- `python scripts/check-docs-commands.py --jekyll-bundle-check` — passing locally after `public_suffix` lockfile regression to 6.0.2 (`cd docs && bundle check`).
- `python -m pytest tests/unit/docs/test_docs_review.py tests/unit/docs/test_code_review_docs_parity.py tests/unit/test_check_docs_commands_script.py tests/unit/test_pre_commit_quality_parity.py -q` — passing.

## OpenSpec

- `openspec validate docs-15-code-review-validation-guardrails --strict` — passing.
- 2026-04-16: Spec delta headers normalized (`## MODIFIED Requirements`, `### Requirement:`, `#### Scenario:`) under `openspec/changes/docs-15-code-review-validation-guardrails/specs/**/spec.md` so strict validation and future `openspec archive` succeed; `openspec validate docs-15-code-review-validation-guardrails --strict` — passing.

## Format / lint

- `hatch run format` and `hatch run lint` — passing for touched Python.

## SpecFact code review

- `hatch run specfact code review run --json --out .specfact/code-review.json --scope changed` — passing (2026-04-15); evidence at `.specfact/code-review.json`.

## Follow-up: bundle permalink vs. `..` links (2026-04-16)

- `hatch run pytest tests/unit/scripts/test_docs_site_validation_link_agreement.py tests/unit/docs/test_docs_review.py::test_authored_internal_docs_links_resolve_to_published_docs_targets -q` — passing.
- `python scripts/check-docs-commands.py` — passing (no findings).
- `hatch run format`, `hatch run lint`, `hatch run type-check` — passing.
- `hatch run contract-test` — passing (624 tests).
- `hatch run specfact code review run --json --out /tmp/code-review-docs15.json scripts/docs_site_validation.py tests/unit/scripts/test_docs_site_validation_link_agreement.py` — **PASS** (`overall_verdict` PASS, `ci_exit_code` 0; report outside gitignored `.specfact/` for inspection).
