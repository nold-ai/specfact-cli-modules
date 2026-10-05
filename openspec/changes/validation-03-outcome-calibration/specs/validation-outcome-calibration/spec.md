## ADDED Requirements

### Requirement: Exploratory outcome pilot

The pilot SHALL begin with 30 changes across the paired SpecFact repositories on the documented Linux CI platform, stratified by declared risk and size. Two reviewers SHALL independently assess decision quality and finding actionability before reconciliation. The baseline workflow and added context/feedback cohort SHALL retain risk, size and workflow/version identity so results are not represented as randomized causal evidence without an appropriate design. The pilot SHALL NOT become a release gate or a blocking specification-quality score.

#### Scenario: Pilot remains exploratory

- **GIVEN** a 30-change pilot with differing risk/size composition
- **WHEN** results are reported
- **THEN** counts and strata are visible and no universal productivity or causal improvement is asserted.

#### Scenario: Reviewers disagree

- **GIVEN** two independent classifications of a finding
- **WHEN** triage is reconciled
- **THEN** both original assessments and the final disposition are retained.

### Requirement: Separate outcome units and unavailable measurements

Outcome records SHALL distinguish human review minutes, clarification minutes, attempts to passing required checks, elapsed seconds, actionable findings, false blocks and escaped defects with an explicit follow-up window. Tokens and monetary costs SHALL be recorded only when measured, with producer/model, units, currency and price timestamp where relevant; missing measurements SHALL be unavailable rather than zero or estimated savings. Data SHALL remain at change/team level and export as versioned JSON/CSV to existing analysis tools without a hosted analytics platform or personal ranking.

#### Scenario: Token usage missing

- **GIVEN** a change without available token/cost instrumentation
- **WHEN** pilot data is exported
- **THEN** those fields remain unavailable and human effort and elapsed time are not substituted as token cost.

#### Scenario: Escape follow-up incomplete

- **GIVEN** a change whose predeclared defect follow-up window has not elapsed
- **WHEN** outcomes are summarized
- **THEN** escaped-defect observations are right-censored or pending rather than zero confirmed escapes.

### Requirement: Uncertainty and operational sample gates

Reports SHALL distinguish observed sample rates from population claims. With zero false blocks in n independent representative known-good observations, the one-sided 95% binomial upper bound SHALL be reported as 1 - 0.05^(1/n), with sampling assumptions. Twenty per pair and 100 aggregate SHALL remain optional assurance operational sample gates, not proof of a population false-block rate at most 1%. A claim using the bound below 1% requires at least 299 zero-failure observations under those assumptions; routine delivery thresholds SHALL NOT be inflated to manufacture that claim.

#### Scenario: Operational samples have uncertainty

- **GIVEN** zero false blocks at n=20 or n=100
- **WHEN** confidence is summarized
- **THEN** the upper bounds are approximately 13.9% and 3.0%, respectively, with the independent representative sampling limitation.

#### Scenario: Repeated correlated observations

- **GIVEN** many retries from the same changes or team
- **WHEN** a population-rate claim is requested
- **THEN** correlation and sampling bias are explicit and the observations are not presented as independent representative proof.
