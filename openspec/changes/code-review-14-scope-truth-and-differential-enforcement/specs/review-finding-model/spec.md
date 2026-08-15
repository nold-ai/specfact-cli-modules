## ADDED Requirements

### Requirement: Independent Finding Lifecycle and Remediation

`ReviewFinding` SHALL represent severity, lifecycle status, differential state, remediation availability, and blocking policy as separate fields. Schema 1.6 differential evidence SHALL also carry `identity_fingerprint`, `occurrence_evidence_digest`, `continuity_anchor_digest`, closed `continuity_status=proven|different|ambiguous|invalid`, and `differential_bucket_digest` from signed `finding-multiset-v1`; raw line/column/span is evidence only and never part of identity. `autofix_available=true` SHALL mean only that a remediation mechanism exists; it SHALL NOT mark an open finding fixed, waived, or non-blocking.

#### Scenario: Fixable error remains open and blocking

- **GIVEN** an introduced error has an available deterministic autofix but the fix has not been applied
- **WHEN** strict policy evaluates it
- **THEN** lifecycle status remains open
- **AND** it blocks according to error policy
- **AND** remediation availability is reported separately.

#### Scenario: Duplicate findings preserve multiplicity

- **GIVEN** base has one finding and head has two analyzer emissions at the same uniquely continuous physical source anchor, with the same line-independent identity fingerprint and unchanged severity/blocking inputs
- **WHEN** `occurrence-continuity-v1` validates the anchor and `finding-multiset-v1` pairs the bucket
- **THEN** one emission is unchanged and the unmatched head emission is introduced
- **AND** base/head counts, deterministic pairing, head surplus, and bucket digest remain evidence
- **AND** the duplicate cannot collapse into one unchanged set member or PASS.

#### Scenario: Line-only shift preserves identity

- **GIVEN** one base/head finding shifts line after an unrelated insertion before its otherwise exact source anchor
- **WHEN** its analyzer/rule/path/symbol/precisely-normalized-message identity and severity/blocking partition match
- **AND** `occurrence-continuity-v1` proves exactly one physical base/head location from identical spanned plus adjacent-line bytes
- **THEN** the deterministic pair is unchanged
- **AND** both raw spans and the anchor evidence remain recorded
- **AND** line movement alone does not create a false fixed/introduced pair.

#### Scenario: Identity-equal replacement at a different source anchor is introduced

- **GIVEN** a base diagnostic is removed and head produces the same analyzer/rule/path/symbol/message/severity/blocking identity at a different source context
- **WHEN** `occurrence-continuity-v1` compares their immutable source anchors
- **THEN** they are not paired unchanged
- **AND** the unmatched head occurrence is introduced and blocks strict PASS
- **AND** the base occurrence follows the ordinary fixed/suppression/rename policy
- **AND** an invalid span or an anchor occurring at multiple physical locations records an invalid/ambiguous unknown transition rather than unchanged or introduced.

#### Scenario: Finding is fixed at head

- **GIVEN** an unmatched base occurrence remains after complete `finding-multiset-v1` pairing at a successfully analyzed head
- **AND** no introduced inline suppression for the same analyzer/path can explain its absence
- **WHEN** differential classification runs
- **THEN** differential state is fixed
- **AND** lifecycle/policy do not treat it as an open blocker
- **AND** aggregate status retains the baseline evidence but excludes that exact fixed baseline-only item from remaining blockers.

#### Scenario: Missing finding across a rename is conservatively unknown

- **GIVEN** a base finding belongs to the old side of a one-to-one rename
- **AND** its normalized fingerprint is absent at head
- **WHEN** differential classification runs under `rename-fix-policy-v1`
- **THEN** the missing finding is unknown, never fixed, regardless of whether the renamed file bytes changed
- **AND** matching normalized findings may remain unchanged and head-only findings may be introduced
- **AND** CR14 performs no semantic-subject inference.

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

