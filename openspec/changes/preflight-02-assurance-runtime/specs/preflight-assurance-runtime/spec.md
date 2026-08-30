## ADDED Requirements

### Requirement: Deterministic pre-implementation loop

The module SHALL execute a stateful pre-implementation loop that discovers a change, captures exact inputs, runs required validators, presents findings, accepts only user-authorized refinement, reruns after changes, records explicit approval, and verifies the resulting seal before implementation.

#### Scenario: Ready change is approved and sealed

- **GIVEN** all required inputs are identified and every required validator returns a determinate non-blocking result
- **WHEN** the user explicitly approves the displayed contract and validation summary
- **THEN** the runtime records an approval seal bound to the exact reviewed identities
- **AND** a subsequent verification step succeeds only while those identities remain current.

#### Scenario: Blocking or unknown result stops the loop

- **GIVEN** a required validator reports a blocking finding, does not complete, or cannot identify an authoritative source
- **WHEN** readiness is aggregated
- **THEN** the runtime reports `BLOCKED` or `UNKNOWN`
- **AND** it does not offer approval or state that implementation may begin.

### Requirement: Read-only default

The preflight command SHALL inspect and render without modifying change artifacts or project state unless an explicit write operation is authorized.

#### Scenario: Default review finds stale tasks

- **GIVEN** an OpenSpec change contains stale tasks
- **WHEN** `specfact preflight run <change-id>` executes without `--write`
- **THEN** it returns structured findings and suggested source-owned refinements
- **AND** no OpenSpec, source, GitHub, or project artifact is changed.

#### Scenario: User authorizes refinement

- **GIVEN** the workflow proposes exact edits to an owning artifact
- **WHEN** the user authorizes those edits
- **THEN** the orchestration applies only the approved edits through the owning workflow
- **AND** the owning workflow reuses the paired core safe-write contract, rejects concurrent source drift, and preserves unrelated user-owned content
- **AND** captures a new source snapshot, binds the predecessor seal where implementation work already exists, preserves the immutable implementation-lineage origin baseline, and reruns every required validator before approval.

### Requirement: Versioned Python validator registry

The module SHALL run validators identified by stable ID and version and SHALL distinguish required from optional validators.

#### Scenario: Required validator is unavailable

- **GIVEN** policy requires a validator that cannot be loaded or completed
- **WHEN** the validator registry runs
- **THEN** the result records the missing validator and reason
- **AND** readiness is `UNKNOWN` rather than successful.

#### Scenario: Optional validator emits advice

- **GIVEN** an optional validator returns an advisory finding
- **WHEN** results are aggregated
- **THEN** the finding remains visible with validator provenance
- **AND** it does not independently convert an otherwise ready result to blocked.

### Requirement: Required MVP validation domains

The initial runtime SHALL validate artifact completeness, source freshness, role-classified scope, component ownership, per-input influence or no-impact disposition, risk-dimension disposition, Requirements-plan identity, dependency readiness, interface ownership, acceptance-testability, and conflicting active work. A no-impact disposition SHALL bind the exact sealed input/path identity and role, its baseline observation identity/digest, a non-empty rationale, and a policy-authorized deterministic permitted-transition predicate identity/version/configuration digest with a closed change class and observable invariants. The predicate SHALL be supported and semantics-preserving for that role, SHALL NOT admit arbitrary content, behavior, configuration, dependency, or execution changes, and SHALL be evaluable by a later checkpoint against exact provenance-bound base/current observations. If those properties cannot be established, the input SHALL require explicit influence mappings instead. Risk validation SHALL require every affected behavior or interface to contain the closed core dimensions `boundary`, `malformed_or_missing_input`, `state_transition`, `idempotency`, `cache`, `error`, `status`, `timeout`, `unknown_precedence`, `path`, `repository_lifecycle`, `platform`, and `compatibility`.

#### Scenario: Scope has no acceptance or test trace

- **GIVEN** a proposed change adds a behavior or interface with no mapped acceptance criterion or test intent
- **WHEN** scope traceability and testability validators run
- **THEN** they emit a blocking finding against the owning artifact path
- **AND** the result identifies the refinement target.

#### Scenario: Source scope cannot select semantic evidence

- **GIVEN** a governed source path has no component owner or bounded pytest targets
- **WHEN** scope and testability validators run
- **THEN** they emit a blocking finding against the source scope entry
- **AND** later implementation checkpoints are not described as selectable.

#### Scenario: Sealed input lacks an influence disposition

- **GIVEN** a non-excluded source, test, docs, generated, or evidence path or a seal-bound test, dependency, policy, toolchain, or relevant configuration input has neither approved influence mappings to every obligation it can affect nor a complete policy-authorized no-impact transition disposition
- **WHEN** scope and testability validators run
- **THEN** readiness is blocked or unknown according to source availability
- **AND** no approval seal is issued with an input that a downstream checkpoint would have to map by inference.

#### Scenario: No-impact disposition cannot constrain the future delta

- **GIVEN** a proposed no-impact disposition omits or ambiguously binds its exact sealed baseline observation, predicate identity/version/configuration, closed permitted change class, observable invariants, or role support, or its predicate admits arbitrary semantic or execution-relevant changes
- **WHEN** scope and testability validators run
- **THEN** readiness is blocked or unknown according to source availability
- **AND** path/role identity plus rationale alone cannot authorize a downstream empty semantic-selector set.

#### Scenario: Risk dimension lacks an explicit disposition

- **GIVEN** an affected behavior omits a closed risk dimension, marks it covered without a complete existing Requirements case at planned maturity or stronger, or marks it not applicable without a rationale
- **WHEN** semantic-risk validation runs
- **THEN** readiness is blocked or unknown according to source availability
- **AND** the missing case is not inferred from filenames or prose.

#### Scenario: Planned covered risk declares its execution stage

- **GIVEN** a covered risk references an existing complete Requirements verification case at `planned` maturity with stable case identity, method, intent, observable, and touchpoints but no authored test
- **WHEN** verification intent is validated
- **THEN** the contract retains the planned mapping/plan and case identities plus `slice`, `commit`, `prepush`, or `ci` as its earliest required stage without fabricating a selector
- **AND** the result records test-authored selector reconciliation as required before production implementation.

#### Scenario: Failing-first test creates the exact selector

- **GIVEN** an approved planned case has no selector and failing-first test authoring produces a Requirements-owned test-authored plan
- **WHEN** preflight validates the refinement
- **THEN** it requires the same requirement/scenario/case identity, method, intent, observable, touchpoints, and declared stage plus a valid exact pytest selector under the existing Requirements contract
- **AND** production implementation waits for explicit approval of a successor seal that binds the predecessor and preserves the implementation-lineage origin baseline.

#### Scenario: GitHub dependency metadata disagrees with proposal

- **GIVEN** proposal dependencies and native GitHub blocked-by relationships differ
- **WHEN** dependency readiness is validated
- **THEN** the mismatch is blocking or unknown according to source availability
- **AND** body-only dependency text cannot satisfy the native relationship check.

### Requirement: Human and JSON rendering parity

The CLI SHALL derive human and JSON output from the same normalized validation result.

#### Scenario: Renderer outputs are compared

- **GIVEN** one completed validation run
- **WHEN** human and JSON renderers emit their representations
- **THEN** readiness, finding IDs, severities, source paths, validator identities, and assurance limits agree
- **AND** rendering does not recompute readiness.

### Requirement: Persisted approval artifacts

Only during an explicitly authorized approval write MAY the runtime atomically persist working copies of the normalized contract, validation result, seal, and lineage-tip response under an ignored project-local, change-specific path; that path SHALL NOT be the canonical cross-checkout approval authority by itself. Seal-aware repository policy SHALL identify a rollback-resistant canonical approval source that is either tracked with governed repository state and anchored to policy-authorized protected base/history outside candidate control, or independently attested by an authenticated append-only/monotonic authority. Either source SHALL be immutable and shareable with a fresh clone or protected consumer and SHALL permit rejection of an older internally valid seal/tip restoration. During that explicitly authorized approval write, the runtime SHALL atomically persist the normalized contract, validation result, seal, canonical lineage-tip record, and their source bindings to the canonical source. The tip SHALL bind the repository, change, and lineage identities, latest seal digest and monotonic sequence, complete predecessor-chain digest, registry/source identity, protected-history or independent-monotonic anchor, and update authority. A successor approval SHALL advance the complete canonical set exactly once; an ancestor seal SHALL NOT remain representable as the current tip. A read-only preflight run SHALL write no local, project, or shared state.

#### Scenario: Persistence is interrupted

- **GIVEN** one requested approval artifact cannot be written or verified
- **WHEN** persistence runs
- **THEN** no partial set is treated as a valid approved contract
- **AND** the runtime reports a non-ready persistence result.

#### Scenario: Canonical lineage tip cannot be established

- **GIVEN** persisted approval artifacts contain a missing, stale, rolled-back, forked, or ambiguously current lineage-tip record
- **WHEN** the approval source is read for checkpoint or conformance handoff
- **THEN** current-seal selection is `UNKNOWN` and non-passing
- **AND** an older valid ancestor seal is not substituted for the canonical latest seal.

#### Scenario: Fresh checkout cannot access required approval authority

- **GIVEN** repository policy or authoritative base provenance requires seal-aware approval state
- **AND** a fresh clone or protected consumer can access only an ignored local cache or cannot authenticate the policy-authorized shared approval source
- **WHEN** the runtime selects a seal or lineage tip
- **THEN** selection is `UNKNOWN` and non-passing rather than `NOT_APPLICABLE`
- **AND** local absence cannot reclassify the governed repository as never sealed.

#### Scenario: Tracked approval state lacks an independent rollback anchor

- **GIVEN** a branch contains an internally valid older seal and matching tip
- **AND** the tracked approval source cannot be verified against policy-authorized protected base/history outside candidate control or an independent append-only/monotonic authority
- **WHEN** the runtime selects canonical approval state
- **THEN** selection is `UNKNOWN` and non-passing
- **AND** the self-contained branch state cannot establish itself as the latest canonical tip.

### Requirement: Canonical skill and slash-command contract

The future module SHALL bundle one canonical `specfact-preflight` workflow that invokes the deterministic CLI and can be exported to harness-native invocation forms.

#### Scenario: Harness invokes bundled workflow

- **GIVEN** a compatible installer exposes the bundled workflow as `/specfact-preflight`, `$specfact-preflight`, or another native alias
- **WHEN** a user selects an OpenSpec change
- **THEN** the workflow invokes the supported preflight CLI and consumes structured output
- **AND** it does not duplicate validator logic in the prompt.

#### Scenario: Workflow encounters ambiguous refinement

- **GIVEN** findings require a material scope or design choice
- **WHEN** the skill presents possible refinements
- **THEN** it pauses for user direction
- **AND** it does not silently change or approve the source artifacts.

### Requirement: Implementation gate instructions

Consumers SHALL be able to reference the workflow from compact AGENTS.md, OpenSpec, Spec Kit, or command-harness instructions without embedding the full validation loop.

#### Scenario: Generated instruction gate is evaluated

- **GIVEN** a harness instruction says to require current preflight approval before implementation
- **WHEN** the referenced workflow is installed
- **THEN** the agent can invoke the canonical loop through the harness-native form
- **AND** the detailed workflow remains sourced from the module-owned skill.
