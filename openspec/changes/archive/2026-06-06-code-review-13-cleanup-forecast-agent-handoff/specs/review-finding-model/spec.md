## MODIFIED Requirements

### Requirement: ReviewFinding schema supports additive simplification metadata

The `ReviewFinding` model SHALL accept optional simplification metadata while preserving the existing governed finding fields and category/severity validation. The report schema version SHALL advance additively when simplification metadata, guided simplification metadata, cleanup forecast metadata, or AI IDE handoff metadata is emitted.

#### Scenario: Finding carries signal trace evidence

- **WHEN** a `ReviewFinding` payload includes `signal_trace`
- **THEN** model validation SHALL accept deterministic signal entries with tool/source name, fired status, optional score/value, evidence references, and explanation
- **AND** legacy finding payloads without `signal_trace` SHALL remain valid

#### Scenario: Finding carries preserve reasons

- **WHEN** a `ReviewFinding` payload includes `preserve_reasons`
- **THEN** each reason SHALL come from a closed taxonomy of preserve contexts
- **AND** the finding SHALL NOT be considered safe for automatic cleanup while a preserve reason is present
- **AND** the preserve reason SHALL include enough evidence for a developer or AI agent to explain why cleanup was not applied

#### Scenario: Finding carries remediation packet

- **WHEN** a simplify-focused finding includes `remediation_packet`
- **THEN** the packet SHALL include a plain-language issue, recommended action, possible keep reason, safety checks, validation plan, and safe-to-autofix flag
- **AND** the packet MAY include patch forecast references when preview evidence exists
- **AND** AI IDE prompts and skills SHALL treat the JSON packet as authoritative over prompt prose
