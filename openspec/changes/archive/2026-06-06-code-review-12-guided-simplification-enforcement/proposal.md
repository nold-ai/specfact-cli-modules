## Why

`code-review-11-simplification-feedback-loop` made simplification findings richer, but the output is still closer to a senior developer's radar than a junior-safe workflow. Users and LLM agents need findings that say whether a cleanup is safe to apply, needs tests, requires design judgment, or should be preserved because it encodes a contract, public API boundary, compatibility shim, or domain intent.

This follow-up turns `specfact code review run --focus simplify` into a guided clean-code workflow for interactive IDE users and headless AI agents. It keeps meaningful contracts and extension points intact while making truly mechanical AI-bloat cleanup clear enough for non-senior developers and LLMs to interpret correctly.

## What Changes

- Extend simplification findings with senior-readable guidance: guidance kind, recommended action, rationale, clean-code principle, safety checks, preserve reason, action status, and before/after improvement evidence.
- Classify simplification findings into `safe_mechanical`, `needs_tests`, `design_judgment`, and `preserve` so agents do not blindly remove meaningful patterns.
- Make `--focus simplify --mode enforce` fail only on unresolved `safe_mechanical` findings.
- Make `--focus simplify --fix` apply only deterministic safe-mechanical rewrites and record what was applied, still recommended, kept, skipped, or failed.
- Upgrade `/specfact.08-simplify` and the `specfact-code-review` skill into adaptive walkthrough surfaces for vibe-coder, junior, senior/pro, and headless-agent usage.
- Keep review JSON backward-compatible and use it as the authoritative evidence artifact.

## Capabilities

### New Capabilities

- `guided-simplification-review`: Senior-grade guidance and evidence for simplify-focused code review workflows.

### Modified Capabilities

- `review-finding-model`: Add optional action-oriented simplification guidance fields.
- `review-run-command`: Add guided enforce/fix behavior for simplify focus.
- `code-review-simplification-feedback`: Upgrade metadata from advisory hints to actionable, LLM-safe guidance.
- `house-rules-skill`: Align the installed skill with the new simplify decision policy.

## Impact

- **Affected bundles:** `packages/specfact-code-review` and `packages/specfact-project`.
- **Affected interfaces:** `.specfact/code-review.json` receives additive optional guidance metadata and report summary fields; existing required fields remain compatible.
- **Affected prompt resources:** `packages/specfact-project/resources/prompts/specfact.08-simplify.md`.
- **Affected skill resources:** `packages/specfact-code-review/src/specfact_code_review/resources/skills/specfact-code-review/SKILL.md`, `skills/specfact-code-review/SKILL.md`, and IDE skill copies.
- **Release impact:** module package version bumps and signature refresh are required when packaged resources or manifests change.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Modules Epic:** [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162)
- **Parent Feature:** [#275](https://github.com/nold-ai/specfact-cli-modules/issues/275)
- **GitHub Issue:** [#286](https://github.com/nold-ai/specfact-cli-modules/issues/286)
- **Repository:** nold-ai/specfact-cli-modules
- **Prior Baseline:** [#276](https://github.com/nold-ai/specfact-cli-modules/issues/276) / `code-review-11-simplification-feedback-loop`
- **Last Synced Status:** proposed
- **Sanitized:** false
