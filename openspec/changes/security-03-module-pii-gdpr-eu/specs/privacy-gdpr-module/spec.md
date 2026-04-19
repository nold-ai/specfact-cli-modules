# Privacy and GDPR Module Specification

## ADDED Requirements

### Requirement: Privacy bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-pii-gdpr` that exposes the `privacy` command and declares truthful bundle dependencies, pip dependencies, and `core_compatibility` entries for `security-01-unified-findings-model` and `security-02-eu-gdpr-baseline` (shared privacy/GDPR findings and EU baseline contracts).

#### Scenario: Bundle manifest is loaded

- **WHEN** SpecFact reads installed module manifests
- **THEN** the privacy bundle is discoverable as an official package with the `privacy` command and valid compatibility metadata

### Requirement: PII and GDPR detections use normalized safe findings

The bundle SHALL translate detector output into the privacy and GDPR finding/report contracts from `security-01-unified-findings-model` and `security-02-eu-gdpr-baseline` and SHALL store only redaction-safe evidence references rather than raw sensitive payloads.

#### Scenario: PII is detected in a prompt or log artifact

- **WHEN** the bundle identifies a configured PII type in analyzed content
- **THEN** it emits a normalized privacy finding that records the PII class and evidence reference without persisting the raw sensitive value

### Requirement: EU and GDPR rule packs affect privacy command outcomes

The bundle SHALL honor the EU/GDPR baseline from `security-02-eu-gdpr-baseline` and the shared policy/profile modes from `policy-02-packs-and-modes` when determining privacy command status and remediation messaging.

#### Scenario: EU residency policy is violated in hard mode

- **WHEN** the bundle evaluates configured residency data and finds a violation while policy mode is hard
- **THEN** it reports a normalized GDPR finding and returns a blocking command outcome
