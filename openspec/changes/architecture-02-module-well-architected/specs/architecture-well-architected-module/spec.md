# Architecture Well-Architected Module Specification

## ADDED Requirements

### Requirement: Architecture bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-architecture` that exposes the `architecture` command and declares truthful bundle dependencies, pip dependencies, and `core_compatibility` for the paired core architecture review contracts.

#### Scenario: Bundle manifest is loaded

- **WHEN** SpecFact reads installed module manifests
- **THEN** the architecture bundle is discoverable as an official package with the `architecture` command and valid compatibility metadata

### Requirement: Boundary and interface analysis uses the shared review contracts

The bundle SHALL translate dependency-boundary, interface-diff, and ADR-traceability analysis into the paired core architecture findings/report contracts instead of defining bundle-local report schemas.

#### Scenario: An import boundary violation is detected

- **WHEN** the bundle evaluates repository dependency rules and finds a forbidden import crossing
- **THEN** it emits a normalized architecture finding with the violated boundary rule and a stable evidence reference

### Requirement: Portable boundary rules support ALLOWED_IMPORTS patterns

The bundle SHALL support portable rule resources derived from `ALLOWED_IMPORTS.md`-style policies so repository owners can encode architecture boundaries without writing provider-specific code.

#### Scenario: Repository policy is expressed through allowed-import rules

- **WHEN** the bundle loads repository boundary policy derived from an `ALLOWED_IMPORTS.md`-style source
- **THEN** it applies those rules during architecture review and classifies violations through the paired core findings contract
