## ADDED Requirements

### Requirement: Enterprise audit bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-enterprise-audit` that exposes audit-related commands and declares truthful bundle dependencies, pip dependencies, and `core_compatibility` for the paired core enterprise audit contracts.

#### Scenario: Bundle manifest is loaded

- **WHEN** SpecFact reads installed module manifests
- **THEN** the enterprise audit bundle is discoverable as an official package with audit commands and valid compatibility metadata

### Requirement: Audit events are signed and privacy-aware

The bundle SHALL serialize governance actions into the paired core audit-event schema, sign the event payloads, and avoid storing raw restricted content in emitted or queued events.

#### Scenario: A governance action triggers audit emission

- **WHEN** the bundle prepares an audit event for a governed action such as rule promotion or approval
- **THEN** it emits a signed, privacy-aware event payload aligned with the paired core schema

### Requirement: Audit delivery supports local queue inspection

The bundle SHALL persist deterministic local queue metadata for audit events that are not yet delivered and SHALL expose inspection or retry commands for those queued events.

#### Scenario: Event delivery is temporarily unavailable

- **WHEN** an audit event cannot be delivered immediately
- **THEN** the bundle records the event in a local queue with deterministic receipt metadata and makes it visible to inspection or retry commands
