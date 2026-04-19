## ADDED Requirements

### Requirement: FinOps bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-finops` that exposes the `finops` command and declares truthful bundle dependencies, pip dependencies, and `core_compatibility` for the paired core FinOps contracts.

#### Scenario: Bundle manifest is loaded

- **WHEN** SpecFact reads installed module manifests
- **THEN** the FinOps bundle is discoverable as an official package with the `finops` command and valid compatibility metadata

### Requirement: Collectors emit normalized FinOps evidence

The bundle SHALL gather provider-reported or local fallback token/cost data and emit evidence files through the paired core FinOps evidence contract rather than a bundle-local schema.

#### Scenario: Provider cost data is available

- **WHEN** the bundle receives provider token and billing data for a session
- **THEN** it writes normalized FinOps evidence with cost, token, source, and outcome fields compatible with the paired core schema

### Requirement: Outcome classification is deterministic

The bundle SHALL classify sessions into the paired core outcome enum using explicit workflow signals and SHALL not require LLM-generated free-form summaries for outcome selection.

#### Scenario: A session leads to rule promotion

- **WHEN** the bundle observes workflow signals showing a completed distillation cycle that promoted a rule
- **THEN** it records the session outcome as `rule-updated` in the normalized FinOps evidence
