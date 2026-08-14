## ADDED Requirements

### Requirement: Explicit Review Scope Evidence

`specfact code review run` SHALL support unambiguous `worktree`, `index`, `range`, and `full` scopes plus explicit positional files. Index scope SHALL analyze the exact staged blob snapshot, not current worktree path content. Range scope SHALL require base and head refs, resolve full base/head and merge-base commit/tree SHAs, select the committed merge-base-to-head delta, and use the merge-base—not the supplied base-ref tip—as the differential baseline. Changed tests SHALL be included by default. `changed` SHALL be a deprecated alias for `worktree`, not PR range. Positional files SHALL emit `assurance_kind=explicit_files` and SHALL NOT satisfy a consumer or policy requiring `pr_range` assurance.

For index mode, `scope.py` SHALL materialize staged blobs outside the caller worktree and record the index tree/blob/content identities so later unstaged edits at the same path cannot affect analysis. For range mode, it SHALL materialize fresh detached merge-base/head roots from the resolved commit trees outside the caller worktree plus a separate sealed merge-base policy bundle. It SHALL manifest each selected analyzer input and declared analyzer-config input by path, Git blob identity, and content digest; pass only materialized-root paths to analyzers; apply one trusted merge-base-policy analyzer/config identity to both range snapshots; pass explicit baseline config paths to configurable adapters; and verify every snapshot manifest before and after analysis. Ruff SHALL use explicit baseline `--config` or `--isolated`, Pylint explicit baseline `--rcfile` or a sealed pinned-default config, basedpyright explicit baseline `--project` rather than `.`, and Semgrep the explicit baseline policy `bundle_root`. Adapter/config injection failure SHALL yield UNKNOWN. Index and range modes SHALL reject `--fix`, `--preview-fixes`, and `--with-mutation`. Any index conflict/object failure, materialization failure, path-root violation, or content-integrity failure SHALL yield UNKNOWN.

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

#### Scenario: Range assurance rejects simplification focus

- **GIVEN** range scope is combined with `--focus simplify`
- **WHEN** the request is validated
- **THEN** it fails before analysis because the simplification queue filters unrelated findings
- **AND** no report from that narrowed run carries `assurance_kind=pr_range`
- **AND** the message directs the caller to a separate worktree or explicit-file simplification workflow.

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
- **AND** the supplied base-ref tip remains recorded as resolver evidence.

#### Scenario: Pure rename preserves an unchanged finding

- **GIVEN** a one-to-one range rename moves a file without changing its bytes and the same blocker is reported at the old base path and new head path
- **WHEN** differential fingerprints are compared
- **THEN** the head anchor is normalized through the recorded rename relation to the old/base path
- **AND** the blocker is classified unchanged rather than fixed at base and introduced at head
- **AND** the report retains both paths and the rename fact.

#### Scenario: Candidate config cannot suppress its own finding

- **GIVEN** the head changes analyzer configuration to suppress a finding that the trusted merge-base policy would report
- **WHEN** merge-base and head snapshots are analyzed
- **THEN** every configurable adapter receives the same explicit sealed merge-base policy bundle
- **AND** no adapter discovers configuration from the head tree, caller worktree, or process current directory
- **AND** the head-side candidate configuration remains scope/shadow evidence but cannot change differential enforcement
- **AND** missing or unusable baseline configuration yields UNKNOWN rather than fallback discovery.

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

Strict PR-range assurance SHALL use the closed schema-versioned `pr-range-v1` profile defined authoritatively in `run/runner.py` and bound in the report by profile ID and policy/config digest. Required analyzer IDs are `ruff`, `radon`, `semgrep`, `ai-bloat-ast`, `ast-clean-code`, `basedpyright`, `pylint`, and `contracts`. `semgrep-bugs` is conditionally required when the trusted merge-base policy snapshot contains the governed bugs configuration; when that configuration is absent its outcome SHALL be NOT_APPLICABLE rather than skipped. The profile has no optional analyzers.

The report SHALL list each profile member with required/conditional status, ran/failed/NOT_APPLICABLE outcome, version, toolchain and configuration digests, duration, and diagnostics. A required analyzer that is unavailable, skipped, failed, timed out, unparsable, or identity-mismatched SHALL make assurance UNKNOWN. Zero findings SHALL count as successful coverage only when an explicit successful run record exists; an empty finding list alone is not analyzer evidence. Analyzer adapters SHALL surface timeout, unavailable, and parse failures explicitly. The required `contracts` member includes the CrossHair subprocess; a CrossHair timeout SHALL record failed contracts coverage and make assurance UNKNOWN rather than returning an empty success.

#### Scenario: Default PR-range profile has closed membership

- **GIVEN** strict range review resolves the `pr-range-v1` profile
- **WHEN** analyzer coverage is planned
- **THEN** the eight always-required analyzer IDs and conditional `semgrep-bugs` membership match the normative profile exactly
- **AND** the profile ID, membership, required flags, versions, and policy/config digest are retained in the report
- **AND** no implementation-specific optionality changes assurance.

#### Scenario: Contract subprocess timeout is unknown

- **GIVEN** the required contracts analyzer starts CrossHair and that subprocess times out
- **WHEN** analyzer coverage is finalized
- **THEN** contracts coverage is failed with the timeout diagnostic
- **AND** the run is UNKNOWN even if contract findings are empty
- **AND** the timeout is never represented as a successful zero-finding run.

#### Scenario: Mandatory analyzer did not run

- **GIVEN** a profile requires an analyzer that does not produce a valid result at either snapshot
- **WHEN** the report finalizes
- **THEN** analyzer coverage identifies the gap
- **AND** no all-passed summary is emitted.

