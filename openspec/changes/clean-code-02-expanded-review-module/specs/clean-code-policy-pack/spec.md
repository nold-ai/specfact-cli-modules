## ADDED Requirements

### Requirement: Clean-Code Policy-Pack Payload
The bundle SHALL ship the `specfact/clean-code-principles` policy-pack payload for downstream policy consumers.

#### Scenario: Built-in pack manifest exposes the clean-code rules
- **GIVEN** the bundle release artifacts are built
- **WHEN** the clean-code pack manifest is inspected
- **THEN** it lists the clean-code rule identifiers required by the 2026-03-22 plan
- **AND** the pack can be installed without a repo-local copy of the rule inventory

#### Scenario: Pack payload stays compatible with per-rule mode overrides
- **GIVEN** a downstream consumer overrides one clean-code rule mode
- **WHEN** the pack manifest is resolved through policy code
- **THEN** the override targets the manifest rule IDs directly
- **AND** the bundle does not invent a second clean-code-specific severity schema
