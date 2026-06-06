## Why

`code-review-12-guided-simplification-enforcement` made simplify findings safer for humans and agents to interpret, but the report still does not quantify cleanup impact or package each recommendation as a portable handoff artifact. Developers need to know how much code is likely removable, how much risk each cleanup carries, and what proof an AI IDE should use before editing.

This change turns `specfact code review run --focus simplify` into a cleanup forecast and remediation handoff loop. It keeps the current conservative guidance model, adds normalized bloat metrics, records deterministic preserve signals, and emits remediation packets that any AI IDE or LLM can consume without relying on vendor-specific prompts.

## What Changes

- Add a `cleanup_forecast` report summary with reviewed LOC, estimated removable LOC ranges, guidance-kind breakdowns, AI-bloat density, weighted bloat points, and cleanup-yield metrics.
- Extend findings with optional `signal_trace`, `preserve_reasons`, and `remediation_packet` fields so each cleanup recommendation carries explainable evidence and an AI-ready action contract.
- Add `--preview-fixes` for simplify-focused runs to compute non-mutating patch and numstat forecasts for supported safe-mechanical fixers.
- Add opt-in `--with-mutation` for mutation-backed proof on simplify candidates without making mutation testing part of the default review path.
- Expand preserve detection for contracts, public APIs, protocol/ABC members, Typer/Click callbacks, compatibility shims, explicit preserve markers, and load-bearing mutation evidence.
- Update modules docs, quickstart, the packaged `specfact-code-review` skill, and command-contract coverage to present the JSON report as the universal AI IDE handoff artifact.

## Capabilities

### New Capabilities

- `cleanup-forecast-review`: Quantified cleanup forecasting and AI-bloat index reporting for simplify-focused review runs.
- `ai-ide-remediation-handoff`: Portable remediation packets for AI IDEs and headless agents.

### Modified Capabilities

- `review-finding-model`: Add optional evidence and handoff fields while preserving legacy report compatibility.
- `review-run-command`: Add non-mutating preview and opt-in mutation proof flags.
- `guided-simplification-review`: Use stronger preserve and proof signals before cleanup recommendations are applied.
- `review-cli-contracts`: Cover the new flags, invalid combinations, and JSON output shape.
- `house-rules-skill`: Teach agents to use cleanup forecasts and remediation packets.

## Impact

- **Affected bundle:** `packages/specfact-code-review`.
- **Affected docs:** Code Review bundle/module pages and AI bloat quickstart.
- **Affected JSON:** `.specfact/code-review.json` receives additive optional fields; existing required fields remain compatible. Custom simplify report paths are allowed only when downstream consumers have been updated to read them.
- **Affected command surface:** `specfact code review run` gains `--preview-fixes` and `--with-mutation`.
- **Release impact:** `specfact-code-review` version, registry entry, and signatures must be refreshed if packaged assets or manifests change.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Modules Epic:** [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162)
- **Parent Feature:** [#275](https://github.com/nold-ai/specfact-cli-modules/issues/275)
- **GitHub Issue:** [#297](https://github.com/nold-ai/specfact-cli-modules/issues/297)
- **Repository:** nold-ai/specfact-cli-modules
- **Prior Baseline:** [#286](https://github.com/nold-ai/specfact-cli-modules/issues/286) / `code-review-12-guided-simplification-enforcement`
- **Last Synced Status:** synced
- **Sanitized:** false
