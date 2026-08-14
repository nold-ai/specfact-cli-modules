## ADDED Requirements

### Requirement: Explicit Review Scope Evidence

`specfact code review run` SHALL support unambiguous `worktree`, `index`, `range`, and `full` scopes plus explicit positional files. Index scope SHALL analyze the exact staged blob snapshot, not current worktree path content. Range scope SHALL require base and head refs, resolve full base/head and merge-base commit/tree SHAs, select the committed merge-base-to-head delta, and use the merge-base—not the supplied base-ref tip—as the differential baseline. Changed tests SHALL be included and `assurance_kind=pr_range` SHALL mean the complete governed merge-base-to-head Python selection. Range SHALL reject `--exclude-tests`, every `--focus` facet, `--path`, `--no-tests`, and `--level` before analysis; this change defines no filtered-range assurance. `changed` SHALL be a deprecated alias for `worktree`, not PR range. Positional files SHALL emit `assurance_kind=explicit_files` and SHALL NOT satisfy a consumer or policy requiring `pr_range` assurance.

For index mode, `scope.py` SHALL materialize staged blobs outside the caller worktree and record the index tree/blob/content identities so later unstaged edits at the same path cannot affect analysis. For range mode, it SHALL materialize fresh detached merge-base/head roots from the resolved commit trees outside the caller worktree plus a separate sealed policy bundle from the resolved target base-ref tip. The supplied base-ref tip SHALL be authorized by the pull-request/CI context, and its exact commit/tree and policy/config manifest SHALL be frozen before analysis; an untrusted, moved, missing, or unreadable target policy identity SHALL yield UNKNOWN. The merge-base remains the source-code baseline, while the current authorized target-tip policy governs both source snapshots. The resolver SHALL manifest each selected analyzer input and declared analyzer-config input by path, Git blob identity, and content digest; pass only materialized-root paths to analyzers; pass explicit target-policy config paths to configurable adapters; and verify every snapshot manifest before and after analysis. Ruff SHALL use explicit target-policy `--config` or `--isolated`, Pylint explicit target-policy `--rcfile` or a sealed pinned-default config, basedpyright explicit target-policy `--project` rather than `.`, and Semgrep the explicit target-policy `bundle_root`. Adapter/config injection failure SHALL yield UNKNOWN. Index and range modes SHALL reject `--fix`, `--preview-fixes`, and `--with-mutation`. Any index conflict/object failure, materialization failure, path-root violation, or content-integrity failure SHALL yield UNKNOWN.

The report SHALL record requested/effective scope, assurance kind, repository root, index tree/blob identities when applicable, supplied base/head commit/tree SHAs, the analyzed merge-base commit/tree SHA, diff digest, selected files/lines and content manifests, rename/deletion facts, filters/facets, trusted policy/config identity, resolver identity, status, and diagnostics.

#### Scenario: Clean PR checkout still reviews committed range files

- **GIVEN** a clean checkout whose head contains committed changes relative to base
- **WHEN** range scope runs with those refs
- **THEN** the committed merge-base-to-head files, including tests, are reviewed
- **AND** worktree emptiness does not produce an empty PR review.

#### Scenario: Index analysis uses staged bytes, not later unstaged edits

- **GIVEN** a tracked pathname has staged content and different additional unstaged worktree edits
- **WHEN** index scope runs
- **THEN** analyzers receive the staged blob bytes from the materialized index snapshot
- **AND** the unstaged bytes do not affect findings, score, or status
- **AND** the report binds the analyzed index tree/blob/content identities.

#### Scenario: Range analysis uses immutable commit materializations

- **GIVEN** full base/head refs resolve successfully
- **WHEN** range analysis starts
- **THEN** analyzers receive only paths under separate detached roots materialized from the resolved merge-base and head commit trees
- **AND** selected inputs and declared analyzer configuration are bound by Git blob identity and content digest before and after analysis
- **AND** mutable files in the caller worktree cannot alter either snapshot result
- **AND** a manifest mismatch yields UNKNOWN with diagnostics.

#### Scenario: Snapshot modes reject mutation-capable options

- **GIVEN** index or range scope is combined with `--fix`, `--preview-fixes`, or `--with-mutation`
- **WHEN** the request is validated
- **THEN** it fails before materialization with an explicit non-mutating range-mode error
- **AND** the message directs the caller to a separate worktree or explicit-file run for mutation workflows.

#### Scenario: Range assurance rejects every narrowing filter

- **GIVEN** range scope is combined with `--exclude-tests`, any `--focus` facet, `--path`, `--no-tests`, or `--level`
- **WHEN** the request is validated
- **THEN** it fails before analysis because the requested run omits governed files, test/analyzer execution, or reported findings
- **AND** no narrowed result carries `assurance_kind=pr_range` or turns a non-empty governed range into NOT_APPLICABLE
- **AND** the message directs the caller to a separately labelled worktree or explicit-file workflow.

#### Scenario: Scope failure is unknown

- **GIVEN** missing/shallow refs, Git error, timeout, or repository mismatch
- **WHEN** scope resolution runs
- **THEN** status is UNKNOWN with diagnostics
- **AND** enforce mode exits non-zero
- **AND** no analyzer result is relabelled unchanged because the scope map is empty.

#### Scenario: Resolved empty range is not applicable

- **GIVEN** range scope resolves successfully but selects no governed Python files after explicit filters
- **WHEN** the report finalizes
- **THEN** status is NOT_APPLICABLE
- **AND** the report retains the scope evidence and exclusions
- **AND** it does not claim code quality passed.

### Requirement: Differential Base-Head Enforcement

Range enforcement SHALL analyze the resolved merge-base and head with identical pinned analyzer versions, configuration digests, and policy. The supplied base-ref tip SHALL NOT be used as the analyzer baseline when it differs from the merge base. Stable fingerprints SHALL classify findings as introduced, fixed, unchanged, or unknown. Before fingerprint comparison, the head file anchor for a resolved one-to-one rename SHALL be normalized to the recorded old/base path; copies and unpaired additions SHALL NOT be rename-normalized, and both original paths plus the rename fact SHALL remain in evidence. Changed-line intersection SHALL be evidence only and SHALL NOT be the sole introduction rule.

#### Scenario: Advanced base-ref tip does not replace the merge-base baseline

- **GIVEN** the target base-ref tip advanced after the feature head diverged
- **WHEN** range differential analysis runs
- **THEN** the baseline analyzer snapshot is the resolved merge-base SHA
- **AND** target-only changes after divergence are not classified as feature-branch fixes or introductions
- **AND** the supplied base-ref tip remains recorded as resolver evidence
- **AND** its authorized target-tip policy/config bundle is applied identically to the merge-base and head source snapshots
- **AND** an untrusted, moved, missing, or unusable target policy identity yields UNKNOWN.

#### Scenario: Pure rename preserves an unchanged finding

- **GIVEN** a one-to-one range rename moves a file without changing its bytes and the same blocker is reported at the old base path and new head path
- **WHEN** differential fingerprints are compared
- **THEN** the head anchor is normalized through the recorded rename relation to the old/base path
- **AND** the blocker is classified unchanged rather than fixed at base and introduced at head
- **AND** the report retains both paths and the rename fact.

#### Scenario: Candidate config cannot suppress its own finding

- **GIVEN** the head changes analyzer configuration to suppress a finding that the trusted target-base-tip policy would report
- **WHEN** merge-base and head snapshots are analyzed
- **THEN** every configurable adapter receives the same explicit sealed policy bundle from the authorized target base-ref tip
- **AND** no adapter discovers configuration from the merge-base source tree, head tree, caller worktree, or process current directory
- **AND** the head-side candidate configuration remains scope/shadow evidence but cannot change differential enforcement
- **AND** missing or unusable target-tip configuration yields UNKNOWN rather than fallback discovery.

#### Scenario: Analyzer identity mismatch is unknown

- **GIVEN** merge-base and head analyzer version, toolchain, policy, or configuration identities differ
- **WHEN** differential classification is requested
- **THEN** the affected comparison is UNKNOWN
- **AND** no finding is classified introduced, fixed, or unchanged from non-identical analyzer inputs
- **AND** strict enforcement exits non-zero with both identities retained.

#### Scenario: Introduced blocker outside added lines still blocks

- **GIVEN** a head change introduces a blocking semantic finding whose reported anchor is outside an added-line range
- **WHEN** base/head results are compared
- **THEN** the new fingerprint is introduced
- **AND** strict differential enforcement blocks it.

#### Scenario: Unchanged baseline blocker remains visible

- **GIVEN** the same stable blocker exists at base and head
- **WHEN** differential classification runs
- **THEN** it is unchanged rather than introduced
- **AND** policy may report it as baseline debt without misattributing it to the PR.

#### Scenario: Baseline analysis cannot be trusted

- **GIVEN** a mandatory base analyzer fails, times out, or cannot parse output
- **WHEN** differential classification runs
- **THEN** affected classifications are unknown
- **AND** strict enforcement exits non-zero after retaining diagnostics.

### Requirement: Mandatory Analyzer Coverage

Strict PR-range assurance SHALL use the closed schema-versioned `pr-range-v1` profile defined authoritatively in `run/runner.py` and bound in the report by profile ID and policy/config digest. Required analyzer IDs are `ruff`, `radon`, `semgrep`, `ai-bloat-ast`, `ast-clean-code`, `basedpyright`, `pylint`, and `contracts`. `semgrep-bugs` is conditionally required when the trusted target-base-tip policy snapshot contains the governed bugs configuration; `targeted-pytest-coverage` is conditionally required when the complete range contains governed production Python. When either condition is absent its outcome SHALL be NOT_APPLICABLE rather than skipped. The profile has no optional analyzers, and range cannot disable the targeted pytest member with `--no-tests`.

The report SHALL list each profile member with required/conditional status, per-snapshot ran/failed/NOT_APPLICABLE outcome, version, toolchain and configuration digests, duration, and diagnostics. For every profile member, the planner SHALL derive eligible inputs independently for the merge-base and head from their immutable manifests. A side with zero eligible inputs MAY record NOT_APPLICABLE only with its snapshot commit/tree, input-class identity, empty eligible-input set, manifest digest, and `absence_reason=no_eligible_inputs_in_snapshot`; this is explicit coverage truth, not a skipped/missing analyzer. If any eligible input exists on that side, NOT_APPLICABLE is forbidden and unavailable, skipped, failed, timed-out, unparsable, or identity-mismatched required analysis SHALL make assurance UNKNOWN. A per-snapshot NOT_APPLICABLE result does not make the whole range NOT_APPLICABLE when the opposite side or the range contains governed Python. This rule covers add-only and delete-only ranges without allowing an adapter's unrecorded empty-file early return to count as success. Zero findings SHALL count as successful coverage only when an explicit successful run record exists; an empty finding list alone is not analyzer evidence. Targeted pytest coverage SHALL bind exact test paths/selectors, pytest/coverage versions, environment/config digest, per-snapshot outcome, and coverage artifact digest. It SHALL be evaluated separately for each snapshot. A snapshot containing any governed production input selected for this member requires a valid targeted run. The general zero-eligible-input rule applies when either side contains no governed production input for this member. In addition, the merge-base side MAY record NOT_APPLICABLE when immutable range evidence proves that every selector needed by the member is introduced after the merge base and therefore structurally absent there; this selector exception SHALL bind the absent paths/selectors and `absence_reason=not_present_at_merge_base`. These explicit absent-side results are neither skipped coverage nor no-tests-collected runs, and the aggregate member remains required on every side containing governed production input. A head snapshot that still contains governed production input but has no selectable/collected tests is UNKNOWN; deletion or loss of head-side test coverage cannot use the baseline-selector-absence exception. Pytest unavailability, timeout, collection/internal/usage error, unexpected no-tests-collected, or missing/unreadable coverage SHALL yield UNKNOWN; collected head assertion failures SHALL yield FAIL; a collected passing run records ran/pass and its coverage findings. Analyzer adapters SHALL surface timeout, unavailable, parse, and documented tool/process-exit failures explicitly. The required `contracts` member includes the CrossHair subprocess; a CrossHair timeout or documented process-error exit (including exit code 2 with no parsed counterexample) SHALL record failed contracts coverage with exit/stderr diagnostics and make assurance UNKNOWN rather than returning an empty success. A successfully parsed CrossHair counterexample remains a contracts finding and SHALL NOT be relabelled as infrastructure uncertainty.

#### Scenario: Default PR-range profile has closed membership

- **GIVEN** strict range review resolves the `pr-range-v1` profile
- **WHEN** analyzer coverage is planned
- **THEN** the eight always-required analyzer IDs plus conditional `semgrep-bugs` and `targeted-pytest-coverage` memberships match the normative profile exactly
- **AND** the profile ID, membership, required flags, versions, and policy/config digest are retained in the report
- **AND** no implementation-specific optionality changes assurance.

#### Scenario: Required analyzers handle structurally empty source snapshots

- **GIVEN** an add-only range whose merge-base has no eligible inputs for a required analyzer, or a delete-only range whose head has no eligible inputs
- **WHEN** analyzer coverage is planned for both snapshots
- **THEN** the structurally empty side records NOT_APPLICABLE with its snapshot identity, input class, empty input set, manifest digest, and `absence_reason=no_eligible_inputs_in_snapshot`
- **AND** every opposite side containing eligible inputs still requires a valid analyzer result
- **AND** an adapter's unrecorded empty-file early return is not successful coverage
- **AND** the whole range remains applicable when governed Python exists on either side.

#### Scenario: Targeted pytest distinguishes product failure from infrastructure uncertainty

- **GIVEN** a complete range contains governed production Python
- **WHEN** targeted pytest coverage executes
- **THEN** the profile records the exact test selection, runner/environment identities, outcome, and coverage artifact digest
- **AND** collected assertion failures produce FAIL
- **AND** unavailable pytest, timeout, collection/internal/usage error, unexpected no collected tests, or missing/unreadable coverage produce UNKNOWN
- **AND** only a merge-base-side input/selector absence proven by immutable range evidence produces NOT_APPLICABLE for that side
- **AND** the stage cannot be omitted by `--no-tests`.

#### Scenario: Targeted pytest handles inputs introduced after the merge base

- **GIVEN** a range introduces governed production input and its targeted test or selector, so those exact inputs are absent from the merge-base tree
- **WHEN** targeted pytest coverage is evaluated for both snapshots
- **THEN** the merge-base side records NOT_APPLICABLE with the absent input/selector manifest and `absence_reason=not_present_at_merge_base`
- **AND** it is not executed as an empty pytest selection and does not become UNKNOWN merely because the new files did not exist
- **AND** the head side still requires collection and a valid coverage artifact
- **AND** a head-side missing selection, no-tests-collected result, or coverage loss is UNKNOWN.

#### Scenario: Contract subprocess timeout or process error is unknown

- **GIVEN** the required contracts analyzer starts CrossHair and that subprocess times out or exits with a documented tool/process error such as code 2 without a parsed counterexample
- **WHEN** analyzer coverage is finalized
- **THEN** contracts coverage is failed with the timeout or exit/stderr diagnostic
- **AND** the run is UNKNOWN even if contract findings are empty
- **AND** timeout or process error is never represented as a successful zero-finding run
- **AND** a successfully parsed counterexample remains a finding rather than an analyzer-process failure.

#### Scenario: Mandatory analyzer did not run

- **GIVEN** a profile requires an analyzer that does not produce a valid result at either snapshot
- **WHEN** the report finalizes
- **THEN** analyzer coverage identifies the gap
- **AND** no all-passed summary is emitted.

