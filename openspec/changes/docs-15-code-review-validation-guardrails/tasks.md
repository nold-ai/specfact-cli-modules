# docs-15: Tasks — code review validation guardrails

## 1. Governance And Readiness

- [x] 1.1 Confirm this change remains scoped to docs, docs validation, pre-commit docs routing, and Code Review docs parity; do not change bundle runtime behavior unless a failing test proves it is required.
- [x] 1.2 Check whether a public GitHub issue is linked or needed; if issue work is required, refresh and consult `.specfact/backlog/github_hierarchy_cache.md` and verify parent, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency before implementation.
- [x] 1.3 Record initial failing evidence in `openspec/changes/docs-15-code-review-validation-guardrails/TDD_EVIDENCE.md` after the failing tests in sections 2 and 3 are added.

## 2. Failing Tests For Docs Validation Categories

- [x] 2.1 Add failing tests for published-route body link validation that catch source-valid but public-broken links such as `run/` from `/bundles/code-review/overview/`.
- [x] 2.2 Add failing tests for published-route-safe links to prove absolute or correctly resolved links pass.
- [x] 2.3 Add failing tests for incomplete published page front matter, including redirect/guide pages missing `title`.
- [x] 2.4 Add failing tests for stable docs finding categories, including `published-link`, `frontmatter`, `command`, `cross-site-link`, `nav-link`, and `docs-build-dependency` where applicable.
- [x] 2.5 Add failing tests for docs build dependency health that expose stale or unresolvable `docs/Gemfile.lock` entries without requiring production deployment.

## 3. Failing Tests For Code Review Docs And Gate Wiring

- [x] 3.1 Add failing tests that compare the documented `specfact code review run` option surface against the Typer command options for `--bug-hunt`, `--mode`, `--focus`, `--level`, and other public behavior-affecting flags.
- [x] 3.2 Add failing tests that require Code Review docs to describe invalid option combinations such as positional files with `--scope` and `--focus` with `--include-tests` or `--exclude-tests`.
- [x] 3.3 Add failing tests proving docs-only staged changes run docs validation before the pre-commit safe-change bypass.
- [x] 3.4 Add failing workflow/script tests proving docs review CI and local pre-commit use the same docs validation categories.

## 4. Docs Validation Implementation

- [x] 4.1 Implement or extract a reusable docs validation helper that builds a published route index from Jekyll front matter and redirect routes.
- [x] 4.2 Implement body link validation that resolves internal links against each page's published route and reports `published-link` findings for missing generated routes.
- [x] 4.3 Implement front matter completeness validation for published pages, with any redirect-stub exemption explicit and tested.
- [x] 4.4 Preserve and integrate existing command-example, legacy-resource, core-doc handoff, config URL, and nav data validations into the shared validation surface.
- [x] 4.5 Implement docs dependency health validation or workflow-level dependency checks that report `docs-build-dependency` failures for unresolvable Jekyll lockfiles.
- [x] 4.6 Update `scripts/check-docs-commands.py` or replace it with a compatibility wrapper that emits the shared validation findings and returns non-zero on any blocking category.

## 5. Docs Content Fixes

- [x] 5.1 Fix Code Review overview "See also" and cross-bundle links so they resolve correctly from `/bundles/code-review/overview/`.
- [x] 5.2 Fix equivalent published-route link defects across bundle overview and deep-dive pages found by the new validator.
- [x] 5.3 Add required front matter metadata to currently incomplete published guide or redirect pages.
- [x] 5.4 Update `docs/bundles/code-review/run.md` to document `--bug-hunt`, `--mode shadow|enforce`, `--focus`, `--level`, progress output, JSON output, test inclusion, and invalid option combinations.
- [x] 5.5 Update `docs/modules/code-review.md` if needed so module notes and the bundle run guide do not contradict each other.
- [x] 5.6 Resolve the docs build dependency lockfile issue or document a justified separate dependency-maintenance follow-up if lockfile mutation is intentionally deferred.

## 6. Local And CI Gate Integration

- [x] 6.1 Update `scripts/pre-commit-quality-checks.sh` so docs-only staged changes run deterministic docs validation before skipping code-specific review and contract-test stages.
- [x] 6.2 Update `.pre-commit-config.yaml` if needed to expose docs validation as a separate visible hook or stage.
- [x] 6.3 Update `.github/workflows/docs-review.yml` so it runs the shared docs validation command and docs unit tests with clear logs for each category.
- [x] 6.4 Update `.github/workflows/docs-pages.yml` so dependency install, Jekyll build, and generated-site validation failures block artifact upload and deployment.
- [x] 6.5 Update workflow/unit tests that assert docs review and pre-commit parity.

## 7. Verification And Evidence

- [x] 7.1 Run `openspec validate docs-15-code-review-validation-guardrails --strict` and record the result.
- [x] 7.2 Run the docs validation command and record the result.
- [x] 7.3 Run `python -m pytest tests/unit/docs/test_docs_review.py tests/unit/test_check_docs_commands_script.py -q` or the updated equivalent docs test slice and record the result.
- [x] 7.4 Run docs dependency/build validation from `docs/` and record the result, including any known network or lockfile constraints.
- [x] 7.5 Run targeted pre-commit/script tests for docs-only safe-change behavior and record the result.
- [x] 7.6 Run required broader quality gates for touched files, including formatting/lint/type checks if Python or workflow helper code changes.
- [x] 7.7 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope changed` during iteration and remediate every finding.
- [x] 7.8 Before PR finalization, rerun SpecFact code review with full or equivalent coverage, ensure `.specfact/code-review.json` is fresh, and record the command and timestamp in `TDD_EVIDENCE.md`.
