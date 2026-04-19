## ADDED Requirements

### Requirement: Resiliency review bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-review-resiliency` that exposes the `review-resiliency` command, declares any required `bundle_dependencies`, and advertises a truthful `core_compatibility` range for the paired core resiliency contracts.

#### Scenario: Bundle is installed for review execution

- **WHEN** SpecFact loads installed module manifests
- **THEN** the resiliency bundle is discoverable as an official package with the `review-resiliency` command and valid compatibility metadata

### Requirement: Resiliency findings map to the shared review contracts

The bundle SHALL translate static rule-pack results and any explicitly enabled probe outputs into the paired core resiliency finding and report models without defining a competing schema in the modules repository.

#### Scenario: Static checks produce resiliency findings

- **WHEN** the bundle detects retry, timeout, idempotency, or graceful-degradation violations
- **THEN** it emits findings categorized for the shared core report contract with stable rule identifiers and deterministic evidence references

### Requirement: Active probes are explicit opt-in behavior

The bundle SHALL keep load-profile or probe-style checks disabled by default and SHALL require explicit command flags or profile configuration before executing any active runtime probe.

#### Scenario: Probe flags are absent

- **WHEN** a user runs the default resiliency review command without enabling probes
- **THEN** the bundle performs only offline-safe static analysis and reports that active probes were skipped by design
