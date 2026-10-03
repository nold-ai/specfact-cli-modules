# Change: Calibrate validation outcomes through an exploratory pilot

## Why

Apply the owner-approved agentic SDLC roadmap to existing Python, OpenSpec/Spec Kit and GitHub users. Preserve the distinction between reviewed assertions, behavior evidence and authenticated authority. This is a bounded follow-up, not a replacement authoring or review engine.

## What Changes

- Exploratory outcome pilot: The pilot SHALL begin with 30 changes across the paired SpecFact repositories on the documented Linux CI platform, stratified by declared risk and size. Two reviewers SHALL independently assess decision quality and finding actionability before reconciliation. The baseline workflow and added context/feedback cohort SHALL retain risk, size and workflow/version identity so results are not represented as randomized causal evidence without an appropriate design. The pilot SHALL NOT become a release gate or a blocking specification-quality score.
- Separate outcome units and unavailable measurements: Outcome records SHALL distinguish human review minutes, clarification minutes, attempts to passing required checks, elapsed seconds, actionable findings, false blocks and escaped defects with an explicit follow-up window. Tokens and monetary costs SHALL be recorded only when measured, with producer/model, units, currency and price timestamp where relevant; missing measurements SHALL be unavailable rather than zero or estimated savings. Data SHALL remain at change/team level and export as versioned JSON/CSV to existing analysis tools without a hosted analytics platform or personal ranking.
- Uncertainty and operational sample gates: Reports SHALL distinguish observed sample rates from population claims. With zero false blocks in n independent representative known-good observations, the one-sided 95% binomial upper bound SHALL be reported as 1 - 0.05^(1/n), with sampling assumptions. Twenty per pair and 100 aggregate SHALL remain optional assurance operational sample gates, not proof of a population false-block rate at most 1%. A claim using the bound below 1% requires at least 299 zero-failure observations under those assumptions; routine delivery thresholds SHALL NOT be inflated to manufacture that claim.

## Capabilities

### New Capabilities

- `validation-outcome-calibration`: calibrate validation outcomes through an exploratory pilot.

### Modified Capabilities

None in this proposal. Existing lean reconciliation and optional assurance retain their own ownership.

## Impact

Planning only in this PR; no runtime, registry, manifest or version changes. Own a bounded experiment protocol, local versioned JSON/CSV exports and analysis instructions. No telemetry platform, default model calls, personal score or runtime gate.

At implementation, update owning command help, adapter/reference and workflow guides on modules.specfact.io, README entry points where needed, frontmatter and navigation for added pages. Additive APIs remain optional; offline parsing/verification remains available. Rollback restores the prior compatible signed core/module pair and disables optional integration without rewriting historical reports.

## Dependencies and delivery

Protocol design is independent. Collection using context/feedback starts only after their exact released producer contracts are available. No outgoing blocker on lean delivery, adapters or optional assurance.

Implementation follows specification, derived tests, meaningful failing-before evidence, code, passing evidence and scope-appropriate gates. Use current repository reality and live issue readiness before work; do not interpret this planning approval as authority to bypass an In Progress owner or signed release gate.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#493](https://github.com/nold-ai/specfact-cli-modules/issues/493)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/493>
- **Repository**: `nold-ai/specfact-cli-modules`
- **Parent Feature**: #163
- **Last Synced Status**: planning / Todo, 2026-10-04

## Research boundary

The roadmap and sources are in [AGENTIC_SDLC_ROADMAP.md](../../AGENTIC_SDLC_ROADMAP.md). Product priority is an owner decision. Productivity, savings, complete hidden-behavior detection and universal independent reviewer recall are not established claims.

## Planning validation

See [AGENTIC_SDLC_VALIDATION.md](../../AGENTIC_SDLC_VALIDATION.md) for actual proposal checks and the explicit Python-only analyzer applicability exception. Runtime review and release tasks remain pending.
