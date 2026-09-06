# Specification: review-installed-payload-layout

## ADDED Requirements

### Requirement: Verified installed package layout

The Code Review runtime SHALL derive and verify installed payloads from exactly one supported src or flat package root without weakening core artifact verification.

#### Scenario: Signed src installation survives archive removal

- **GIVEN** a signed official package installed through core with src/specfact_code_review and the archive removed
- **WHEN** C14 derives the installed handoff and copies the payload
- **THEN** the handoff succeeds, all required package resources are copied with verified bytes and modes, and a built-in analyzer starts

#### Scenario: Flat staging remains compatible

- **GIVEN** a supported flat installation or authenticated candidate staging root
- **WHEN** C14 computes its manifest and copies its payload
- **THEN** existing canonical flat paths and digests remain compatible

### Requirement: Unsafe or changed payload rejection

The Code Review runtime SHALL fail closed when the installed package root or verified payload cannot be determined safely.

#### Scenario: Missing ambiguous or symlinked roots

- **GIVEN** an absent package root, both supported roots, or a symlink in the selected package path
- **WHEN** C14 verifies the installed payload
- **THEN** it returns UNKNOWN with an actionable handoff/layout reason and executes no built-in analyzer

#### Scenario: Payload changes before copying

- **GIVEN** a verified manifest whose source bytes or file mode subsequently differ
- **WHEN** C14 copies that entry
- **THEN** copying fails closed instead of accepting the changed payload

### Requirement: Installed release regression evidence

The correction SHALL be verified against real core installation contracts and distinguish layout recovery from unrelated assurance failures.

#### Scenario: Compatibility and independent blockers

- **GIVEN** signed src-layout fixture coverage for core 0.55.1 and 0.55.4
- **WHEN** the future implementation reruns handoff, copy, analyzer startup, and the Linux range reproduction
- **THEN** layout failures are eliminated, compatibility evidence is recorded, and remaining policy/runtime UNKNOWN results remain explicit
