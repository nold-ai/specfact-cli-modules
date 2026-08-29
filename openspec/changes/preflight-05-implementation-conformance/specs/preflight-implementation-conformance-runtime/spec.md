## ADDED Requirements

### Requirement: Separate development checkpoint command

The module SHALL expose `specfact preflight checkpoint <change-id>` with `worktree` or `index` scope and `slice`, `commit`, or `deep` profile, and SHALL return the released core local checkpoint result without modifying the approved seal.

#### Scenario: No staged production change or associated seal

- **GIVEN** the pre-commit wrapper finds no staged production path or no seal associated with any staged production path
- **WHEN** automatic checkpoint selection runs
- **THEN** the result is `NOT_APPLICABLE` and exits zero
- **AND** an unsealed repository does not acquire a universal blocking policy.

#### Scenario: A matching seal covers only part of the staged production scope

- **GIVEN** at least one staged production path associates with a valid seal
- **AND** another staged production path is outside that seal
- **WHEN** automatic checkpoint selection runs
- **THEN** every uncovered path is reported as `unexpected`
- **AND** the result is `FAIL` and exits non-zero
- **AND** intentional expansion returns to preflight refinement and reapproval.

#### Scenario: Applicable checkpoint evidence is ambiguous

- **GIVEN** one or more staged production paths are covered by a seal but the seal, Git identity, component owner, selector, runner, or required evidence is stale, multiple, missing, or ambiguous
- **WHEN** checkpoint status is aggregated
- **THEN** the result is `UNKNOWN` and exits non-zero
- **AND** no renderer or workflow converts it to pass.

### Requirement: Bounded checkpoint profiles

The module SHALL define `slice`, `commit`, and `deep` profiles whose selected obligations are derived from the sealed execution stages.

#### Scenario: Slice profile runs immediate semantic evidence

- **GIVEN** changed source paths map to sealed `slice` obligations
- **WHEN** the slice profile runs
- **THEN** it verifies the seal and scope, runs the affected exact Requirements pytest cases, and imports changed-scope code-review evidence
- **AND** it does not run unrelated component or full-repository tests.

#### Scenario: Commit profile evaluates the staged index

- **GIVEN** exactly one valid seal covers staged production paths
- **WHEN** the commit profile runs
- **THEN** it adds every affected component's bounded pytest targets and current-run JUnit evidence
- **AND** execution is bound to the captured index capsule rather than a differing worktree.

#### Scenario: Deep profile encounters CI-only obligation

- **GIVEN** a sealed obligation has earliest stage `ci`
- **WHEN** the deep local profile runs
- **THEN** the obligation is reported as deferred with identity and reason
- **AND** it is not described as locally passed or missing.

### Requirement: Complete implementation scope evidence

The runtime SHALL reuse C14 worktree/index/range primitives and implement the released core snapshot matrix without guessing or lossy path parsing. Worktree snapshots SHALL bind repository identity, full base commit ID, and worktree-manifest digest and include staged, unstaged, and untracked state. Index snapshots SHALL bind repository identity, full base commit ID, and exact index tree ID and exclude untracked paths unless staged as additions. Range snapshots SHALL bind repository identity, full base/head commit IDs, and base/head tree IDs and SHALL NOT represent untracked paths. Every manifest SHALL preserve additions, deletions, both rename endpoints, before/after modes, symlink target identity, and byte-preserving path identity; rename interpretation SHALL be bound to producer, policy, and toolchain identity.

#### Scenario: Repository contains difficult path transitions

- **GIVEN** a change adds, deletes, renames, changes mode, symlinks, or uses quoted, Unicode, or trailing-character paths
- **WHEN** the implementation snapshot is extracted
- **THEN** every path and both rename endpoints are preserved with exact transition identity
- **AND** unresolved Git evidence yields `UNKNOWN`.

### Requirement: Seal-bound semantic evidence selection

The runtime SHALL map changed source paths through sealed component ownership, risk rows, Requirements plan identities, exact pytest cases, bounded component targets, and execution stages. It MAY select a subset of requirement, scenario, verification-case, and exact pytest-selector identities already bound by the seal; any addition, removal, replacement, or change of a bound identity SHALL require preflight validation, approval, and a new seal.

#### Scenario: Production path lacks semantic ownership

- **GIVEN** a changed production path has no sealed component or required semantic evidence mapping
- **WHEN** checkpoint selection runs
- **THEN** the result is `UNKNOWN`
- **AND** overall pytest success cannot satisfy the missing obligation.

#### Scenario: Implementation exceeds sealed scope

- **GIVEN** a changed path or behavior lies outside sealed roles and exclusions
- **WHEN** checkpoint comparison runs
- **THEN** it returns an `unexpected` failure and a `return_to_preflight` remediation class
- **AND** intentional expansion requires a new preflight review and seal.

### Requirement: Current-run pytest and code-review evidence

The runtime SHALL first supply the upstream design contract, validation result, seal, policy, and current source identities to released core verification, then reuse existing Requirements pytest/JUnit and SpecFact code-review JSON contracts with exact producer and snapshot identities. It SHALL use released core finding precedence and deterministic `FAIL`/`UNKNOWN`/`PASS` aggregation rather than redefining them.

#### Scenario: Selector is missing, duplicate, uncollected, failed, or stale

- **GIVEN** required pytest evidence cannot be reconciled exactly to the selected snapshot and plan
- **WHEN** checkpoint evidence is normalized
- **THEN** the result is `FAIL` for a determinate violation or `UNKNOWN` for unresolved provenance
- **AND** no alternate selector grammar or historical overall exit code is accepted.

#### Scenario: Cache identity changes

- **GIVEN** the seal, snapshot, obligation set, pytest targets, runner, policy, toolchain, or relevant configuration changes
- **WHEN** cached evidence is considered
- **THEN** the prior cache entry is rejected
- **AND** required checks execute again.

### Requirement: Local and range authority separation

The runtime SHALL preserve core checkpoint authority for worktree/index results and SHALL require repository identity, full immutable base/head commit IDs, and base/head tree identities for `specfact preflight conform <change-id>`. Tree attestations and the complete path manifest SHALL bind to that exact repository and range.

#### Scenario: Local pass is presented as PR proof

- **GIVEN** a worktree or index checkpoint passed
- **WHEN** a consumer requests final or protected PR authority
- **THEN** the runtime rejects promotion
- **AND** requires a new immutable-range conformance or protected consumer run.

### Requirement: Compact bounded remediation workflow

The module SHALL emit deterministic compact remediation packets and bundle a harness-neutral workflow that permits at most three agent fix/rerun cycles.

#### Scenario: Finding can return to implementation

- **GIVEN** a determinate finding is classified `fix_implementation`, `fix_or_add_test`, or `rerun`
- **WHEN** the workflow hands it to the current coding agent
- **THEN** the packet includes fingerprint, contract/risk reference, implementation evidence, expected observable, recommended action, and validation selectors
- **AND** the deterministic CLI itself performs no LLM or network call.

#### Scenario: Workflow must stop

- **GIVEN** a fingerprint repeats consecutively, three cycles are exhausted, scope expands, status is `UNKNOWN`, design judgment is required, or a sealed artifact would change
- **WHEN** the workflow evaluates the next action
- **THEN** it stops and reports the human or preflight handoff
- **AND** it does not edit or reseal the contract automatically.

### Requirement: Human and JSON parity with optional persistence

Human and JSON renderers SHALL derive from one normalized result, and explicit persistence SHALL atomically retain the complete snapshot/result without modifying the original contract or seal.

#### Scenario: Persistence or rendering is incomplete

- **GIVEN** output cannot preserve all status, authority, finding, packet, evidence, policy, and assurance-limit identities
- **WHEN** rendering or persistence runs
- **THEN** no partial artifact is treated as valid checkpoint or conformance evidence
- **AND** the original preflight artifacts remain unchanged.

### Requirement: Shadow dogfood before seal-aware blocking

The first rollout SHALL measure checkpoint behavior in shadow mode and SHALL enable blocking only for repositories with an applicable valid seal after the accepted defect corpus shows no false PASS or destructive/ambiguous behavior.

#### Scenario: C14 regression fixture is exercised

- **GIVEN** an accepted fixture represents an illegal exit, cache identity drift, malformed input, deletion-only change, difficult path, suppression relocation, or FAIL/UNKNOWN precedence defect
- **WHEN** slice or commit checkpoint dogfood runs
- **THEN** the defect is non-passing before simulated PR delivery
- **AND** duration, local detection, cycles, packet size, repeated class, and later-review outcome are recorded.

### Requirement: Signed publication before adapter consumption

The implementation SHALL version, sign, compatibility-test, and publish one immutable #434 module release identity whose signed manifest separately binds the existing preflight workflow identity/digest and the new implementation-check workflow identity/digest before #251/#253/#433 consume them.

#### Scenario: Adapter requests the new workflow

- **GIVEN** #433 prepares a harness adapter
- **WHEN** it resolves the canonical module and workflow identities
- **THEN** it consumes the exact signed #434 module identity, preflight workflow identity/digest, and implementation-check workflow identity/digest
- **AND** #434 contains no harness-specific adapter package.
