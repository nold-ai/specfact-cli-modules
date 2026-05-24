## MODIFIED Requirements

### Requirement: ReviewFinding schema supports additive simplification metadata

The `ReviewFinding` model SHALL accept optional simplification metadata while preserving the existing governed finding fields and category/severity validation. The report schema version SHALL advance additively when simplification metadata or guided simplification metadata is emitted.

#### Scenario: Simplification metadata validates on a finding

- **WHEN** a `ReviewFinding` payload includes existing simplification metadata such as `confidence`, `rewrite_hint`, `canonical_pattern`, `intent_key`, `estimated_deletion_lines`, or `related_locations`
- **THEN** model validation SHALL accept the payload when the original required fields are valid
- **AND** `related_locations` SHALL use stable file and line references compatible with existing evidence references

#### Scenario: Guided simplification metadata validates on a finding

- **WHEN** a `ReviewFinding` payload includes `guidance_kind`, `recommended_action`, `clean_code_principle`, `rationale`, `safety_checks`, `preserve_reason`, `action_status`, `before_ref`, `after_ref`, or `improvement`
- **THEN** model validation SHALL accept the payload when the original required fields are valid
- **AND** guided findings SHALL accept an omitted `action_status` until a recommendation lifecycle status is known
- **AND** a finding with `guidance_kind="preserve"` SHALL require a non-empty `preserve_reason`
- **AND** legacy finding payloads SHALL remain valid without any guided simplification fields
