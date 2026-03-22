# OpenSpec change order by module and dependency

## Implemented (archived)

| Change | Status / Date |
|--------|---------------|
| ✅ backlog-02-migrate-core-commands | archived 2026-03-10 |
| ✅ backlog-bundle-local-source-alignment | archived 2026-03-10 |
| ✅ bugfix-backlog-html-export-validation | archived 2026-03-10 |
| ✅ modules-pre-commit-quality-parity | archived 2026-03-10 |
| ✅ registry-republish-outdated-bundles | archived 2026-03-10 |
| ✅ fix-issue-49-ado-provider-field-type-coercion | archived 2026-03-11 |
| ✅ code-review-02-ruff-radon-runners | archived 2026-03-17 |
| ✅ code-review-04-contract-test-runners | archived 2026-03-17 |
| ✅ code-review-07-house-rules-skill | archived 2026-03-17 |
| ✅ code-review-08-review-run-integration | archived 2026-03-17 |
| ✅ code-review-10-review-scope-modes | archived 2026-03-17 |
| ✅ docs-01-modules-docs-canonical-site | archived 2026-03-17 |
| ✅ fix-backlog-add-ado-custom-field-payload | archived 2026-03-17 |
| ✅ fix-backlog-add-work-item-type-mapping | archived 2026-03-17 |
| ✅ fix-backlog-provider-required-field-mappings | archived 2026-03-17 |
| ✅ review-run-dogfood-followup | archived 2026-03-17 |
| ✅ docs-cli-command-alignment | archived 2026-03-20 |

## Plan-derived addendum (2026-03-22 clean code enforcement plan)

- `clean-code-02-expanded-review-module` is the next modules-repo change.
- It expands the code-review bundle with clean-code finding categories, new analysis runners, the clean-code policy-pack payload, and the house-rules skill update consumed by specfact-cli.
- It is sequenced after the archived code-review runner and review-run changes and before specfact-cli change `clean-code-01-principle-gates`.

## Pending

### Code review bundle expansion

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| clean-code | 02 | clean-code-02-expanded-review-module | [#94](https://github.com/nold-ai/specfact-cli-modules/issues/94) | specfact-cli/code-review-zero-findings (#423); code-review-02 ✅; code-review-04 ✅; code-review-07 ✅; code-review-08 ✅; code-review-10 ✅ |
