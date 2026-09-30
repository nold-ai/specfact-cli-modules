## ADDED Requirements

### Requirement: Portable Deterministic Orchestration

The workflow module SHALL own execution sequencing and consume existing producer interfaces through configured adapters. Public APIs SHALL use contract/type validation. Requirements reconciliation SHALL remain separate and side-effect-free. Pre-validation and verification SHALL NOT edit source/index content or require an LLM.

#### Scenario: External repository without Hatch or internal wiki

- **GIVEN** a repository with supported configured checks and no SpecFact contributor layout
- **WHEN** local workflow verification runs
- **THEN** applicable checks use that configuration without requiring these repositories or internal wiki files.

#### Scenario: Required tool is missing

- **GIVEN** an applicable required gate whose tool or supported schema is unavailable
- **WHEN** verification runs
- **THEN** it is blocked with an actionable diagnostic; optional checks are explicitly not evaluated, never silently passed.

### Requirement: Independent Producer Outcomes

The workflow SHALL retain original producer artifacts, identities and outcomes. Its actionable findings projection SHALL preserve producer references and SHALL NOT modify Code Review scores or derive a required gate PASS from missing findings. R09 and C15 SHALL remain the owners of their evidence and policy semantics.

#### Scenario: Review passes while a required test fails

- **GIVEN** a PASS review report and a failing current test result
- **WHEN** the workflow projects findings and summarizes checks
- **THEN** the test remains failing and the requested full verification cannot pass.

#### Scenario: A repair affects a different gate

- **GIVEN** an edit prompted by a lint finding also affects tests or policy inputs
- **WHEN** recheck selects gates
- **THEN** all affected gates run or reuse valid matching outputs; uncertain applicability selects the complete lane.

### Requirement: Exact Scoped Input Binding

Results SHALL bind exact scoped content, reviewed planning inputs, effective configuration and relevant producer/environment identities. Run IDs SHALL be unique and separate from input digests. Source/index changes during execution SHALL invalidate the result. Semantic determinism SHALL exclude observational fields and SHALL qualify live-service snapshots.

#### Scenario: Dirty content changes at the same HEAD

- **GIVEN** two runs with the same HEAD and dirty flag but different source, index or relevant untracked content
- **WHEN** identities are computed
- **THEN** their input digests differ and the earlier result cannot satisfy the later request.

#### Scenario: Scope selection is index rather than worktree

- **GIVEN** a partially staged file with different unstaged content
- **WHEN** index verification runs
- **THEN** checks evaluate the exact materialized index snapshot and preserve the original index/worktree.

#### Scenario: Inputs change while a producer executes

- **GIVEN** an initial input snapshot and a concurrent edit to an applicable input
- **WHEN** the producer completes
- **THEN** its output is retained diagnostically but cannot establish a passing result for the current request.

### Requirement: Disposable Local Progress

Receipts SHALL be atomic, versioned local operational state with preserved budgets and one active controller per worktree. Standalone verification and ordinary CI SHALL NOT require earlier local phases, RED history or receipts. Local state SHALL NOT confer protected CI authority.

#### Scenario: A fresh session has no receipts

- **GIVEN** valid current inputs and no local turn directory
- **WHEN** standalone verification is requested
- **THEN** current checks run without reconstructing earlier sessions and chronology remains unclaimed.

#### Scenario: A process crashes after reserving a repair attempt

- **GIVEN** persisted attempt accounting and incomplete work
- **WHEN** the run resumes
- **THEN** it retains consumed budget, verifies current identities and reconciles incomplete work instead of treating it as success.

### Requirement: Bounded Remediation and Honest Readiness

Local repair SHALL default to three iterations and the configured time limits, preserve effective producer/contributor policy, and stop on no progress or oscillation. Drift SHALL distinguish observations from invalidity. Explicit optional assurance SHALL retain its own requirements without becoming an ordinary prerequisite.

#### Scenario: Repair makes no progress or exhausts its budget

- **GIVEN** unchanged content/findings after repair, a repeated content/findings pair or exhausted limits
- **WHEN** blocking findings remain
- **THEN** the loop stops with remaining findings and a non-passing outcome.

#### Scenario: A new capability is absent before implementation

- **GIVEN** a valid ADDED delta and no canonical capability yet
- **WHEN** readiness evaluates referenced capabilities
- **THEN** absence alone is not classified as invalid planning.

### Requirement: Signed Current-Run Producer Compatibility Precedes Adoption

Runtime Requirements integration and adoption SHALL validate the exact immutable signed #481 publication, schema-v3 `current_execution` capability, archive/manifest/payload identities and compatibility with the actual core and selected #483 workflow versions before selecting that combination for use. Existing representative current-result fixtures SHALL exercise the installed combination. Missing, unsigned, incompatible or v2-only producers SHALL leave runtime adoption not ready; receipts and legacy-schema fallbacks SHALL NOT satisfy this gate. Repository projection MAY proceed independently, and core #740 SHALL retain its policy cutover ownership.

#### Scenario: Workflow package is signed but its Requirements producer is incompatible

- **GIVEN** a valid signed #483 workflow package and an absent, unsigned, incompatible or v2-only #481 Requirements producer
- **WHEN** runtime integration or core adoption readiness is checked
- **THEN** the combination is rejected as not ready with an actionable diagnostic
- **AND** independent repository projection can proceed without claiming runtime readiness.

#### Scenario: Installed signed producer and workflow match the actual core

- **GIVEN** exact signed #481/#483 identities compatible with the actual core candidate and the v3 current-execution contract
- **WHEN** the installed combination passes the existing representative acceptance fixtures
- **THEN** the compatibility prerequisite is satisfied for that exact combination
- **AND** this does not activate or replace the separate R09 required-policy cutover.
