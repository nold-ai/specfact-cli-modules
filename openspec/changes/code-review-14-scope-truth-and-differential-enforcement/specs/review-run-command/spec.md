## ADDED Requirements

### Requirement: Explicit Review Scope Evidence

`specfact code review run` SHALL support unambiguous `worktree`, `index`, `range`, and `full` scopes plus explicit positional files. Range scope SHALL require base and head refs, resolve full base/head and merge-base commit/tree SHAs, and select the committed merge-base-to-head delta. Changed tests SHALL be included by default. `changed` SHALL be a deprecated alias for `worktree`, not PR range. Positional files SHALL emit `assurance_kind=explicit_files` and SHALL NOT satisfy a consumer or policy requiring `pr_range` assurance.

For range mode, `scope.py` SHALL materialize fresh detached base/head roots from the resolved commit trees outside the caller worktree. It SHALL manifest each selected analyzer input and declared analyzer-config input by path, Git blob identity, and content digest; pass only materialized-root paths to analyzers; apply one trusted base-policy analyzer/config identity to both snapshots; and verify the manifests before and after analysis. Range mode SHALL reject `--fix`, `--preview-fixes`, and `--with-mutation`. Any materialization, path-root, or content-integrity failure SHALL yield UNKNOWN.

The report SHALL record requested/effective scope, assurance kind, repository root, commit/tree SHAs, merge base, diff digest, selected files/lines and content manifests, rename/deletion facts, filters/facets, trusted policy/config identity, resolver identity, status, and diagnostics.

#### Scenario: Clean PR checkout still reviews committed range files

- **GIVEN** a clean checkout whose head contains committed changes relative to base
- **WHEN** range scope runs with those refs
- **THEN** the committed merge-base-to-head files, including tests, are reviewed
- **AND** worktree emptiness does not produce an empty PR review.

#### Scenario: Range analysis uses immutable commit materializations

- **GIVEN** full base/head refs resolve successfully
- **WHEN** range analysis starts
- **THEN** analyzers receive only paths under separate detached roots materialized from the resolved commit trees
- **AND** selected inputs and declared analyzer configuration are bound by Git blob identity and content digest before and after analysis
- **AND** mutable files in the caller worktree cannot alter either snapshot result
- **AND** a manifest mismatch yields UNKNOWN with diagnostics.

#### Scenario: Range mode rejects mutation-capable options

- **GIVEN** range scope is combined with `--fix`, `--preview-fixes`, or `--with-mutation`
- **WHEN** the request is validated
- **THEN** it fails before materialization with an explicit non-mutating range-mode error
- **AND** the message directs the caller to a separate worktree or explicit-file run for mutation workflows.

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

Range enforcement SHALL analyze base and head with identical pinned analyzer versions, configuration digests, and policy. Stable fingerprints SHALL classify findings as introduced, fixed, unchanged, or unknown. Changed-line intersection SHALL be evidence only and SHALL NOT be the sole introduction rule.

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

The report SHALL list each required and optional analyzer with ran/skipped/failed status, version, configuration digest, duration, and diagnostics. A mandatory analyzer that is unavailable, skipped, failed, timed out, or unparsable SHALL make assurance UNKNOWN.

#### Scenario: Mandatory analyzer did not run

- **GIVEN** a profile requires an analyzer that does not produce a valid result at either snapshot
- **WHEN** the report finalizes
- **THEN** analyzer coverage identifies the gap
- **AND** no all-passed summary is emitted.

