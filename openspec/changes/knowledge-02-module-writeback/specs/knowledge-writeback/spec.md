# Knowledge Writeback Module Specification

## ADDED Requirements

### Requirement: Writeback bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-knowledge-writeback` that exposes writeback commands and declares truthful bundle dependencies, pip dependencies, and `core_compatibility` for the paired core knowledge contracts.

#### Scenario: Bundle manifest is loaded

- **WHEN** SpecFact reads installed module manifests
- **THEN** the writeback bundle is discoverable as an official package with writeback commands and valid compatibility metadata

### Requirement: Every writeback target supports preview before mutation

The bundle SHALL generate previews or drafts for every supported writeback target before applying any file mutation or external-comment payload preparation.

#### Scenario: A user selects a file target for writeback

- **WHEN** the user requests writeback into an instruction file
- **THEN** the bundle first produces a preview showing the generated changes and source rule references before any file is updated

### Requirement: Writeback emits deterministic lineage metadata

The bundle SHALL record deterministic metadata that identifies source rules, target type, target destination, and generation timestamps for each writeback operation. Generation timestamps MUST be normalized to a caller-provided deterministic run timestamp (for example `run_start_time`) when supplied; if absent, timestamps MUST be the writeback tool’s own run-start instant. Every recorded timestamp MUST use UTC in ISO-8601 with second precision (`YYYY-MM-DDThh:mm:ssZ`) without fractional seconds or local offsets, and any timestamps supplied in inputs MUST be normalized to that exact format and timezone before persistence so manifests remain reproducible.

#### Scenario: A writeback draft is generated

- **WHEN** the bundle produces a draft for a configured target
- **THEN** it also writes a deterministic output manifest describing which approved rules were projected into that target
