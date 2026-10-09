# Design: Calibrate validation outcomes through an exploratory pilot

## Ownership and public boundary

Own a bounded experiment protocol, local versioned JSON/CSV exports and analysis instructions. No telemetry platform, default model calls, personal score or runtime gate.

Use existing Bridge Adapter, plugin registration and requirement/evidence extension surfaces. Keep producer-original records separate from normalized presentation. Parsing and digest evaluation are side-effect free; runtime adapters own invocation, filesystem snapshots and explicitly selected external access. No new graph engine, hosted service or unrestricted shell runner is introduced.

## Decisions

### Exploratory outcome pilot

The pilot SHALL begin with 30 changes across the paired SpecFact repositories on the documented Linux CI platform, stratified by declared risk and size. Two reviewers SHALL independently assess decision quality and finding actionability before reconciliation. The baseline workflow and added context/feedback cohort SHALL retain risk, size and workflow/version identity so results are not represented as randomized causal evidence without an appropriate design. The pilot SHALL NOT become a release gate or a blocking specification-quality score.

### Separate outcome units and unavailable measurements

Outcome records SHALL distinguish human review minutes, clarification minutes, attempts to passing required checks, elapsed seconds, actionable findings, false blocks and escaped defects with an explicit follow-up window. Tokens and monetary costs SHALL be recorded only when measured, with producer/model, units, currency and price timestamp where relevant; missing measurements SHALL be unavailable rather than zero or estimated savings. Data SHALL remain at change/team level and export as versioned JSON/CSV to existing analysis tools without a hosted analytics platform or personal ranking.

### Uncertainty and operational sample gates

Reports SHALL distinguish observed sample rates from population claims. With zero false blocks in n independent representative known-good observations, the one-sided 95% binomial upper bound SHALL be reported as 1 - 0.05^(1/n), with sampling assumptions. Twenty per pair and 100 aggregate SHALL remain optional assurance operational sample gates, not proof of a population false-block rate at most 1%. A claim using the bound below 1% requires at least 299 zero-failure observations under those assumptions; routine delivery thresholds SHALL NOT be inflated to manufacture that claim.

## Dependencies and rollout

Protocol design is independent. Collection using context/feedback starts only after their exact released producer contracts are available. No outgoing blocker on lean delivery, adapters or optional assurance.

Start additive behavior in shadow/advisory mode where appropriate. Preserve independent required checks. Review exact core/module version and signed payload identities before adoption. Roll back by disabling optional context/hooks/projection or restoring the prior compatible signed pair; retain reports with their original schema, statuses and limitations.

## Verification boundaries

Every spec scenario becomes an independently meaningful fixture or integration assertion before behavior changes. Test negative identities, missing/ambiguous input and source preservation rather than merely mirroring data classes. Reports of planning inspection do not claim execution. Use pytest structured identities first and declare unsupported platforms/producers explicitly.
