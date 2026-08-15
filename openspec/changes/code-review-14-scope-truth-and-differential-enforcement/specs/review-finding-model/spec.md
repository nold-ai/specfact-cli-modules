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
- **AND** no introduced inline suppression for the same analyzer/path can explain its absence
- **WHEN** differential classification runs
- **THEN** differential state is fixed
- **AND** lifecycle/policy do not treat it as an open blocker
- **AND** aggregate status retains the baseline evidence but excludes that exact fixed baseline-only item from remaining blockers.

#### Scenario: Rename without semantic-subject change cannot fix a finding

- **GIVEN** a one-to-one rename has identical file bytes or an unchanged manifest-bound analyzer/rule-specific semantic-subject digest
- **AND** the base finding is absent at head
- **WHEN** differential classification runs
- **THEN** the missing finding is unknown, never fixed
- **AND** unrelated edits elsewhere in the renamed file do not satisfy subject change
- **AND** unavailable or ambiguous subject derivation also yields unknown.

#### Scenario: Matching fingerprint with changed severity is not unchanged

- **GIVEN** base and head observations have the same stable identity fingerprint after rename normalization
- **AND** their normalized severity or derived blocking inputs differ
- **WHEN** differential classification runs
- **THEN** both observations and the transition are retained
- **AND** differential state is unknown under CR14, never unchanged or silently fixed
- **AND** strict assurance cannot PASS until a later signed profile defines and validates that transition.

#### Scenario: Introduced result-control directive remains an open blocker

- **GIVEN** the head adds, changes, or relocates a registered suppression or analyzer-result control directive
- **WHEN** strict differential policy evaluates its immutable directive fingerprint
- **THEN** a separate class-specific finding remains open and blocking: `introduced_inline_suppression` for diagnostic suppressions or `introduced_analyzer_result_control` for every recognized basedpyright or CrossHair analyzer-result control
- **AND** any missing base finding for the same analyzer/path is unknown rather than fixed
- **AND** CR14 accepts no suppression-waiver input or trusted flag and always leaves this finding blocking
- **AND** remediation availability is independent from lifecycle status
- **AND** authenticated exception handling remains a separate `governance-02-exception-management` capability.

#### Scenario: Waiver field is reserved but inactive in C14

- **GIVEN** C14 derives an open finding under schema 1.6
- **WHEN** lifecycle and blocking policy are evaluated
- **THEN** nullable `waiver_reference` is unset and cannot change blocking
- **AND** no CLI, report attachment, context, or injected trusted flag can populate an authenticated waiver
- **AND** future signed ingestion/verification remains owned by `governance-02-exception-management`.

### Requirement: Ledger Preserves Authoritative Assurance Status

For ReviewReport schema 1.6 or newer, the first-party review ledger SHALL consume and persist authoritative `assurance_status` rather than deriving ledger behavior from legacy `overall_verdict`. Persisted local and Supabase ledger status SHALL support PASS, FAIL, UNKNOWN, and NOT_APPLICABLE; PASS_WITH_ADVISORY remains accepted only for legacy reports older than 1.6.

UNKNOWN and NOT_APPLICABLE SHALL be neutral audit events: the run metadata and findings remain recorded, applied reward/coins are zero, pass and block streak counters remain unchanged, and no pass bonus or block penalty is triggered. Local and Supabase run records SHALL store the complete canonical schema 1.6 report in `report_json` with its SHA-256 `report_digest`, including scope/analyzer diagnostics even when `findings` is empty.

#### Scenario: Unknown review is neutral in the ledger

- **GIVEN** a valid schema 1.6 report has assurance_status UNKNOWN and legacy overall_verdict FAIL
- **WHEN** the ledger records it
- **THEN** the persisted authoritative ledger verdict is UNKNOWN
- **AND** reward and applied last delta are zero
- **AND** pass and block streaks are unchanged
- **AND** the legacy FAIL projection does not create a block-streak event
- **AND** report_json and report_digest preserve the UNKNOWN scope/analyzer evidence even when findings are empty.

#### Scenario: Mixed known failure and uncertainty remains a blocking ledger event

- **GIVEN** a valid schema 1.6 report has aggregate assurance_status FAIL, `has_unknown_required_evidence=true`, one valid blocking finding, and one required UNKNOWN member
- **WHEN** the ledger records it
- **THEN** the persisted authoritative ledger verdict is FAIL and existing FAIL reward/streak policy applies
- **AND** report_json and report_digest retain the unknown flag, member status, and diagnostics
- **AND** the ledger does not reinterpret the aggregate as neutral UNKNOWN or claim analyzer coverage was complete.

#### Scenario: Not-applicable review is neutral in the ledger

- **GIVEN** a valid schema 1.6 report has assurance_status NOT_APPLICABLE and legacy overall_verdict PASS_WITH_ADVISORY
- **WHEN** the ledger records it
- **THEN** the persisted authoritative ledger verdict is NOT_APPLICABLE
- **AND** reward and applied last delta are zero
- **AND** pass and block streaks are unchanged
- **AND** no pass streak or coin bonus is awarded
- **AND** report_json and report_digest preserve the no-governed-impact evidence.

#### Scenario: Legacy ledger behavior remains readable

- **GIVEN** a report older than schema 1.6, the exact schema-less `ledger update` payload with run_id/timestamp/score 85/empty findings/summary, or an existing local/Supabase ledger record
- **WHEN** the ledger reads PASS, PASS_WITH_ADVISORY, or FAIL, or normalizes that schema-less fixture to legacy schema 1.0/reward delta 5/PASS/exit 0 while preserving its supplied fields
- **THEN** the prior reward and streak behavior remains compatible
- **AND** updated local models and Supabase check constraints also accept UNKNOWN and NOT_APPLICABLE
- **AND** nullable report_json/report_digest columns keep existing Supabase rows readable
- **AND** no missing new field is inferred as either new authoritative state.

