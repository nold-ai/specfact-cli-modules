## ADDED Requirements

### Requirement: Truthful Review Assurance Status

The governed review report schema `1.6` SHALL expose authoritative `assurance_status` as `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE` plus derived `has_unknown_required_evidence`. `WAIVED` SHALL be a governance overlay, not a verifier-produced status. NOT_APPLICABLE SHALL require successfully resolved no-governed-impact evidence. Otherwise aggregate precedence is FAIL for any validated blocker, UNKNOWN only when required uncertainty exists without a known blocker, and PASS only when neither exists. A mixed FAIL/UNKNOWN report SHALL retain every unknown member and set the derived flag while aggregate remains FAIL.

#### Scenario: Mandatory evidence is unknown

- **GIVEN** scope or a mandatory analyzer is unknown and no valid completed blocker already proves FAIL
- **WHEN** enforce-mode reporting completes
- **THEN** assurance is UNKNOWN and process exit is non-zero
- **AND** partial facts/findings remain available
- **AND** the human summary does not say all validations passed.

#### Scenario: Mixed valid failure and uncertainty has deterministic precedence

- **GIVEN** one required member has valid completed blocking evidence and another required member is UNKNOWN
- **WHEN** schema 1.6 aggregate status is derived
- **THEN** assurance_status is FAIL and non-shadow exit is 1
- **AND** `has_unknown_required_evidence` is true
- **AND** the UNKNOWN member and diagnostics remain in the report
- **AND** ledger and compatibility consumers do not reinterpret the report as neutral UNKNOWN or complete FAIL evidence.

#### Scenario: Schema 1.6 dual-writes a conservative legacy projection

- **GIVEN** a schema 1.6 report has assurance PASS, FAIL, UNKNOWN, or NOT_APPLICABLE
- **WHEN** compatibility fields are serialized
- **THEN** PASS writes legacy PASS or PASS_WITH_ADVISORY according to remaining advisories
- **AND** FAIL writes legacy FAIL
- **AND** UNKNOWN writes legacy FAIL rather than a green verdict
- **AND** NOT_APPLICABLE writes PASS_WITH_ADVISORY plus explicit no-governed-impact text
- **AND** the non-shadow `ci_exit_code` values for PASS, FAIL, UNKNOWN, and NOT_APPLICABLE are respectively 0, 1, 1, and 0.

#### Scenario: Post-analysis enrichment preserves schema 1.6 truth

- **GIVEN** a schema 1.6 report is enriched after analysis, including by cleanup forecast refresh or `--requirements-evidence` context attachment
- **WHEN** the enriched report is returned or persisted
- **THEN** schema_version, assurance_status, scope_evidence, analyzer_coverage, overall_verdict, and ci_exit_code are preserved unchanged
- **AND** Requirements attachment adds only the validated requirements context and does not hard-code schema 1.5
- **AND** enrichment may add its own evidence but cannot downgrade the report to a legacy schema or recompute assurance.

#### Scenario: Signed consumer matrix covers every authoritative status

- **GIVEN** the schema 1.6 Code Review package is built for release
- **WHEN** producer and consumer compatibility is validated
- **THEN** the checked-in signed consumer matrix contains canonical PASS, FAIL, UNKNOWN, and NOT_APPLICABLE reports
- **AND** each case binds required authoritative fields—including runtime trust model, adversarial-runtime capability, and per-member observation trust—permitted legacy projection, and strict/shadow exit behavior
- **AND** the matrix contains a hostile-candidate-policy case whose candidate-executing evidence and aggregate status are UNKNOWN
- **AND** it contains a mixed valid-blocker/required-UNKNOWN case whose aggregate is FAIL, unknown flag is true, and member evidence is retained
- **AND** contradictory status, precedence, legacy verdict, or exit combinations are invalid cases
- **AND** core's staged pre-commit helper remains `explicit_files` while consuming authoritative status
- **AND** no core PR-range consumer is accepted unless it passes the exact released matrix digest.

#### Scenario: Modules staged consumer preserves schema 1.6 UNKNOWN

- **GIVEN** the modules repository staged explicit-files helper receives a valid schema 1.6 report with `assurance_status=UNKNOWN`, `ci_exit_code=1`, and no error finding on a staged changed line
- **WHEN** `scripts/pre_commit_code_review.py` derives its hook exit
- **THEN** authoritative schema 1.6 status and exit remain UNKNOWN/non-zero
- **AND** changed-line blocker fallback is not applied to schema 1.6 or newer
- **AND** only reports older than 1.6 retain the existing staged-line compatibility calculation
- **AND** the helper remains `explicit_files` and does not claim `pr_range`.

#### Scenario: Minimum advertised core runtime loads schema 1.6

- **GIVEN** a candidate Code Review package proposes `core_compatibility: '>=0.56.0,<1.0.0'`
- **WHEN** the pre-release compatibility gate runs in a fresh environment
- **THEN** it checks out the immutable core 0.56.0 tag at the full commit/tree recorded in the checkpoint, installs that core plus the candidate module package, loads the module through core, and validates every schema 1.6 consumer-matrix status/projection
- **AND** an unavailable or mismatched identity, branch fallback, install/load failure, or matrix failure blocks release and the compatibility declaration
- **AND** this smoke proves minimum-version load/schema interoperability only; protected PR-context verification remains the separate downstream core adoption contract.

#### Scenario: Legacy enforcement mode is policy, not scope

- **GIVEN** schema 1.6 dual-writing is enabled
- **WHEN** enforcement and scope are serialized
- **THEN** request mode enforce normalizes to legacy enforcement_mode full
- **AND** an omitted enforcement option with range scope normalizes to strict full, while omission on the deprecated changed/worktree path retains changed
- **AND** full, changed, and shadow retain their legacy values when explicitly valid
- **AND** changed mode is accepted only with the deprecated changed/worktree compatibility path
- **AND** explicit range plus changed mode is rejected
- **AND** strict range writes enforcement_mode full, shadow range writes shadow, and scope_evidence alone identifies range.

#### Scenario: Versioned readers never infer new truth from old fields

- **GIVEN** a report older than schema 1.6
- **WHEN** compatibility reading completes
- **THEN** legacy PASS or PASS_WITH_ADVISORY may yield only PASS and legacy FAIL may yield only FAIL
- **AND** UNKNOWN or NOT_APPLICABLE is never inferred
- **AND** schema 1.6 or newer with missing/invalid assurance_status is invalid/unknown and cannot pass.

#### Scenario: Shadow preserves unknown while exiting zero

- **GIVEN** the same unknown evidence under shadow mode
- **WHEN** reporting completes
- **THEN** process exit may be zero for rollout
- **AND** report assurance remains UNKNOWN
- **AND** no field rewrites the unknown claim to pass.

### Requirement: Review CLI Contracts Cover Explicit Scope and Differential Evidence

Static CLI contract fixtures SHALL cover argv parsing and serialized report/error contracts for worktree, index, range, full, positional files, deprecated changed alias, required full refs, assurance/enforcement status projection, positional PR-range downgrade rejection, and invalid option combinations. Stateful Git content/topology behavior—staged-versus-unstaged index content, merge-base selection with an advanced base-ref tip, changed-test inclusion, empty range, Git failure, immutable materialization, merge-base/head classifications, and analyzer identity/coverage—SHALL be proved only in the allowlisted scope/differential unit and end-to-end tests that create isolated temporary repositories.

#### Scenario: Stateful Git setup is outside static CLI fixtures

- **GIVEN** a case requires index mutation, unstaged overlap, branch divergence, missing refs, or controlled analyzer outcomes
- **WHEN** verification is assigned
- **THEN** it uses `test_scope.py`, `test_differential.py`, or the named review-run e2e module with a temporary repository
- **AND** the static CLI-contract YAML and its existing harness are not extended to perform repository setup
- **AND** no stateful case is claimed from argv-only fixture evidence.

#### Scenario: Range contract requires base and head

- **GIVEN** range scope is requested without one required ref or together with positional files
- **WHEN** the CLI parses the request
- **THEN** it fails with a bounded error and a supported invocation example.

#### Scenario: Positional files cannot satisfy pull-request assurance

- **GIVEN** positional files are supplied to a consumer or policy that requires pull-request range assurance
- **WHEN** the request is validated
- **THEN** it is rejected before analysis because base, head, and merge-base evidence is absent
- **AND** the protected-CI alternative is `--scope range --base-ref <full-ref> --head-ref <full-ref> --pr-context-file <runner-temp-file> --enforcement full`
- **AND** the producer result with matching claimed context is `range_candidate`, while the same local command without context is `range_preview`; neither is merge authority without the protected verification envelope
- **AND** positional files remain valid for explicitly labelled non-PR `assurance_kind=explicit_files` runs.

#### Scenario: Canonical repository merge guidance uses complete PR range

- **GIVEN** a developer or agent follows the mandatory repository quality gate, module/bundle guide, or generated Code Review instructions
- **WHEN** the guidance describes merge or pull-request assurance
- **THEN** protected CI uses `--scope range`, full base/head identities, an event-derived `--pr-context-file` outside the checkout, and `--enforcement full`
- **AND** the producer emits `assurance_kind=range_candidate`, never pr_range
- **AND** the protected consumer independently derives the expected merge base, complete governed diff, selected Python files/lines, governed policy path/section manifests and candidate-policy-change digest, status/rename/deletion manifests, and authorized target-tip policy/config selection; requires approved signed producer module/schema/profile/toolchain plus workflow/job/artifact provenance; then compares every identity and digest with the immutable report
- **AND** its envelope binds every compared identity/manifest/digest and rejects any omitted governed Python or policy input, or merge-base, diff, selection, rename/deletion, policy/config, producer, or artifact mismatch as UNKNOWN
- **AND** only its separate verification envelope emits `effective_assurance_kind=pr_range`
- **AND** manual guidance without context is `assurance_kind=range_preview` and directs merge authority to that protected envelope
- **AND** it does not use changed/worktree or positional branch-delta files as merge evidence
- **AND** the local pre-commit positional gate and simplification worktree workflow are labelled non-PR assurance
- **AND** tracked skill copies are regenerated from the bundled source and remain byte-consistent.

#### Scenario: Installed merge-quality guidance uses PR range

- **GIVEN** Code Review guidance is installed or refreshed through `rules init` or `rules update`
- **WHEN** the generated house rules or bundled skill describe merge-quality review
- **THEN** they use `--scope range`, full base/head ref placeholders, and `--enforcement full`
- **AND** they do not present changed/worktree or positional files as pull-request assurance
- **AND** simplification-preview guidance may retain worktree scope because it is a local mutation workflow
- **AND** range plus any focus, exclude-tests, path filter, no-tests, or level filter is documented and tested as invalid for complete PR assurance.

