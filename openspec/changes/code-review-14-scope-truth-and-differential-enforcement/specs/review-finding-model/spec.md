## ADDED Requirements

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

### Requirement: Ledger Preserves Authoritative Assurance Status

For ReviewReport schema 1.6 or newer, the first-party review ledger SHALL consume and persist authoritative `assurance_status` rather than deriving ledger behavior from legacy `overall_verdict`. Persisted local and Supabase ledger status SHALL support PASS, FAIL, UNKNOWN, and NOT_APPLICABLE; PASS_WITH_ADVISORY remains accepted only for legacy reports older than 1.6.

UNKNOWN and NOT_APPLICABLE SHALL be neutral audit events: the run metadata and findings remain recorded, applied reward/coins are zero, pass and block streak counters remain unchanged, and no pass bonus or block penalty is triggered.

#### Scenario: Unknown review is neutral in the ledger

- **GIVEN** a valid schema 1.6 report has assurance_status UNKNOWN and legacy overall_verdict FAIL
- **WHEN** the ledger records it
- **THEN** the persisted authoritative ledger verdict is UNKNOWN
- **AND** reward and applied last delta are zero
- **AND** pass and block streaks are unchanged
- **AND** the legacy FAIL projection does not create a block-streak event.

#### Scenario: Not-applicable review is neutral in the ledger

- **GIVEN** a valid schema 1.6 report has assurance_status NOT_APPLICABLE and legacy overall_verdict PASS_WITH_ADVISORY
- **WHEN** the ledger records it
- **THEN** the persisted authoritative ledger verdict is NOT_APPLICABLE
- **AND** reward and applied last delta are zero
- **AND** pass and block streaks are unchanged
- **AND** no pass streak or coin bonus is awarded.

#### Scenario: Legacy ledger behavior remains readable

- **GIVEN** a report older than schema 1.6 or an existing local/Supabase ledger record
- **WHEN** the ledger reads PASS, PASS_WITH_ADVISORY, or FAIL
- **THEN** the prior reward and streak behavior remains compatible
- **AND** updated local models and Supabase check constraints also accept UNKNOWN and NOT_APPLICABLE
- **AND** no missing new field is inferred as either new authoritative state.

