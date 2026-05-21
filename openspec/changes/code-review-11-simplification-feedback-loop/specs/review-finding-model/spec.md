## ADDED Requirements

### Requirement: ReviewFinding schema supports additive simplification metadata

The `ReviewFinding` model SHALL accept optional simplification metadata while preserving the existing governed finding fields and category/severity validation. The report schema version SHALL advance additively to `1.1` when simplification metadata is emitted.

#### Scenario: Simplification metadata validates on a finding

- **WHEN** a `ReviewFinding` payload includes `confidence`, `rewrite_hint`, `canonical_pattern`, `intent_key`, `estimated_deletion_lines`, or `related_locations`
- **THEN** model validation SHALL accept the payload when the original required fields are valid
- **AND** `related_locations` SHALL use stable file and line references compatible with existing evidence references

#### Scenario: Legacy finding payload remains valid

- **WHEN** a `ReviewFinding` payload contains only the existing required fields and optional `evidence_refs`
- **THEN** model validation SHALL continue to accept the payload
- **AND** the absence of simplification metadata SHALL NOT change category, severity, blocking, or scoring behavior
