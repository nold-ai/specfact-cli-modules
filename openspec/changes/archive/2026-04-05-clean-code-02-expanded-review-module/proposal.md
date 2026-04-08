# Change: Expanded clean-code review module for specfact-cli-modules

## Why

The 2026-03-22 clean-code plan requires the review engine to move beyond the initial Ruff, Radon, contract, and review-run plumbing. The `specfact-code-review` bundle now needs first-class clean-code coverage across the 7 principles so specfact-cli and external projects can consume a single governed review module rather than a patchwork of repo-local rules. This change owns that review-engine expansion in `specfact-cli-modules`.

## What Changes

- **NEW**: `clean-code-analysis` capability covering the expanded clean-code finding schema, semgrep naming rules, solid/yagni/dry runners, and PR checklist enforcement.
- **MODIFY**: `radon-runner` to emit LOC, nesting-depth, and parameter-count findings under the staged Phase A thresholds from the 2026-03-22 plan.
- **MODIFY**: `review-run-command` to orchestrate the new clean-code runners and expose their results in the governed review report.
- **MODIFY**: `review-cli-contracts` so CLI review scenarios can assert the new clean-code categories and PR-mode behavior.
- **NEW**: `clean-code-policy-pack` capability that ships the `specfact/clean-code-principles` policy-pack payload consumed by specfact-cli `policy-02-packs-and-modes`.
- **NEW**: `house-rules-skill` capability update that compresses the 7-principle clean-code charter into the canonical `skills/specfact-code-review/SKILL.md` surface.

## Capabilities

### New Capabilities

- `clean-code-analysis`: The review bundle emits governed findings for naming, kiss, yagni, dry, solid, and PR checklist rules.
- `clean-code-policy-pack`: The review bundle ships the built-in `specfact/clean-code-principles` pack manifest and rule mapping payload.
- `house-rules-skill`: The canonical review skill exposes the 7-principle clean-code charter in a compact form suitable for downstream IDE integrations.

### Modified Capabilities

- `radon-runner`: Extended from complexity-only findings to staged KISS metric findings.
- `review-run-command`: Extended to orchestrate the new clean-code analysis runners and PR-mode checklist validation.
- `review-cli-contracts`: Extended to cover clean-code categories and PR-mode review scenarios.

## Impact

- **Affected package**: `packages/specfact-code-review/` including finding models, runners, rule payloads, skill distribution, docs, and release metadata.
- **Dependencies**: depends on archived modules-repo runner work (`code-review-02`, `code-review-04`, `code-review-07`, `code-review-08`, `code-review-10`) and on the specfact-cli prerequisite `code-review-zero-findings` remaining the dogfood baseline.
- **Versioning**: bump `specfact-code-review` from `0.44.0` to `0.45.0` because new clean-code categories extend the review schema.
- **Documentation**: update `docs/modules/code-review.md`, the skill documentation, and any bundle release notes describing review categories and policy-pack payloads.
- **Rollback**: if a runner proves too noisy, the pack can keep the rule advisory by default while the runner remains shipped; do not fork the finding schema per consumer.

## Source Tracking

- **GitHub Issue**: #94
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/94
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: open
