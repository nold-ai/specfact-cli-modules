## MODIFIED Requirements

### Requirement: Independent Finding Lifecycle and Remediation

`ReviewFinding` SHALL represent severity, lifecycle status, differential state, remediation availability, and blocking policy as separate fields. `autofix_available=true` SHALL mean only that a remediation mechanism exists; it SHALL NOT mark an open finding fixed, waived, or non-blocking.

#### Scenario: Fixable error remains open and blocking

- **GIVEN** an introduced error has an available deterministic autofix but the fix has not been applied
- **WHEN** strict policy evaluates it
- **THEN** lifecycle status remains open
- **AND** it blocks according to error policy
- **AND** remediation availability is reported separately.

#### Scenario: Finding is fixed at head

- **GIVEN** a stable fingerprint exists at base and not at successfully analyzed head
- **WHEN** differential classification runs
- **THEN** differential state is fixed
- **AND** lifecycle/policy do not treat it as an open blocker.

#### Scenario: Waiver is governance evidence

- **GIVEN** a valid external waiver references an open finding fingerprint
- **WHEN** policy is evaluated
- **THEN** the report retains the detector finding and waiver reference separately
- **AND** the verifier does not claim the finding itself passed.

