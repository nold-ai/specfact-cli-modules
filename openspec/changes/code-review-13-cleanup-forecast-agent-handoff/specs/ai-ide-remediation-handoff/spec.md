## ADDED Requirements

### Requirement: Review JSON is the portable AI IDE handoff contract

The Code Review bundle SHALL expose cleanup guidance through machine-readable JSON so Claude, Codex, Cursor, Copilot, and other assistants can act without vendor-specific prompt assumptions.

#### Scenario: Remediation packets guide AI cleanup

- **WHEN** a simplify-focused report contains cleanup findings
- **THEN** each actionable finding SHALL include or be able to derive a remediation packet
- **AND** the packet SHALL state whether the finding may be auto-fixed, needs tests, needs design judgment, or should be preserved
- **AND** the packet SHALL include a validation plan for any accepted cleanup

#### Scenario: AI instructions prioritize the JSON contract

- **WHEN** `specfact code review run --instructions` is executed
- **THEN** the instructions SHALL tell assistants to generate simplify evidence first
- **AND** they SHALL tell assistants to sort findings by `guidance_kind`, inspect `cleanup_forecast`, and follow remediation packets before editing
- **AND** they SHALL prohibit treating `ai_bloat` findings as proof of AI authorship
