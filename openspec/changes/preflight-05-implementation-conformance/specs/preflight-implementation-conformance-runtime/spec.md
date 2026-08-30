## ADDED Requirements

### Requirement: Separate development checkpoint command

The module SHALL expose `specfact preflight checkpoint <change-id>` with `worktree` or `index` scope and `slice`, `commit`, or `deep` profile, and SHALL return the released core local checkpoint result without modifying the approved seal. Allowed pairs are `slice/worktree`, `slice/index`, `commit/index`, `deep/worktree`, and `deep/index`; every other pair SHALL be rejected as invalid usage before snapshot extraction, without silently overriding either argument. Automatic selection SHALL validate the canonical tip, complete predecessor chain, approval authority, and required Git identities before evaluating path coverage. Applicability and coverage SHALL be computed from the selected snapshot: `worktree` includes staged, unstaged tracked, and untracked changes, while `index` includes staged changes only. The pre-commit wrapper SHALL use `index`; it SHALL NOT make staged-only selection govern an explicit `worktree` checkpoint. Absence of Git approval artifacts SHALL NOT establish absence of approval history: before returning `NOT_APPLICABLE` for a never-sealed repository or paths unrelated to every seal, the runtime SHALL require the policy-authorized canonical approval source to confirm that no current or historical applicable approval exists. Missing, stale, multiple, rolled-back, forked, unavailable, or ambiguous canonical/Git state SHALL return `UNKNOWN`; uncovered governed-path `FAIL` applies only after one valid canonical seal and snapshot identity are established.

#### Scenario: No selected-scope seal-relevant change or associated seal

- **GIVEN** the policy-authorized canonical approval source authoritatively confirms that no current or historical applicable approval exists, neither the authoritative base nor the selected worktree/index snapshot contains working approval state, and no selected-scope approval-artifact path is changed; or it confirms that every path changed in the selected scope is deterministically outside the repository's configured preflight-governed path/input universe and unrelated to every current or prior seal
- **WHEN** automatic checkpoint selection runs
- **THEN** the result is `NOT_APPLICABLE` and exits zero
- **AND** an unsealed repository does not acquire a universal blocking policy.

#### Scenario: Canonical approval is independent of Git artifacts

- **GIVEN** neither the authoritative base nor the selected snapshot contains approval artifacts but the policy-authorized independent canonical source contains a current applicable seal or historical applicable approval
- **WHEN** automatic checkpoint selection runs
- **THEN** the runtime evaluates that canonical approval and the selected-scope changes instead of returning `NOT_APPLICABLE`
- **AND** a current seal proceeds to coverage while historical state prevents the repository from being treated as never sealed.

#### Scenario: Canonical approval history cannot be established

- **GIVEN** Git approval artifacts are absent and the policy-authorized canonical source is unavailable, unauthenticated, stale, rolled back, forked, or ambiguous
- **WHEN** automatic checkpoint selection evaluates applicability
- **THEN** the result is `UNKNOWN` and exits non-zero
- **AND** missing canonical history is never converted to `NOT_APPLICABLE`.

#### Scenario: Worktree checkpoint has only unstaged or untracked changes

- **GIVEN** a valid applicable seal exists and governed changes appear only as unstaged tracked or untracked worktree paths
- **WHEN** `slice/worktree` or `deep/worktree` selection runs with an empty staged index
- **THEN** applicability, coverage, and obligations are evaluated from the complete worktree snapshot and the result is not `NOT_APPLICABLE` merely because the index is empty
- **AND** the staged-only rule remains limited to the separate index-based pre-commit wrapper.

#### Scenario: Staged change removes the last approval state

- **GIVEN** the authoritative base contains a seal or canonical lineage-tip artifact and the staged index deletes, relocates, or replaces that approval state so current-index discovery finds no valid seal
- **WHEN** automatic checkpoint selection runs
- **THEN** the base-to-index approval-state transition is classified as governed and the result is `UNKNOWN` with exit one
- **AND** the repository is not treated as never sealed, whether or not other governed paths are staged.

#### Scenario: Governed selected-scope paths have no covering seal

- **GIVEN** the repository contains one or more preflight seals and at least one path/input changed in the selected worktree/index scope is classified by repository policy as preflight-governed but is covered by no seal role
- **WHEN** automatic checkpoint selection runs
- **THEN** every wholly uncovered governed path/input is `unexpected`, the result is `FAIL`, and the hook exits non-zero
- **AND** absent or ambiguous governed/unrelated classification returns `UNKNOWN`, never `NOT_APPLICABLE`.

#### Scenario: A matching seal covers only part of the selected seal-relevant scope

- **GIVEN** at least one source, test, docs, generated, evidence, or seal-bound configuration path changed in the selected worktree/index scope associates with a valid seal
- **AND** another selected-scope non-excluded seal-relevant path is outside that seal
- **WHEN** automatic checkpoint selection runs
- **THEN** every uncovered path is reported as `unexpected`
- **AND** the result is `FAIL` and exits non-zero
- **AND** intentional expansion returns to preflight refinement and reapproval.

#### Scenario: Applicable checkpoint evidence is ambiguous

- **GIVEN** one or more paths changed in the selected worktree/index scope are covered by a seal but the canonical tip/chain, Git identity, component owner, influence mapping, selector, runner, or required evidence is stale, multiple, missing, or ambiguous
- **WHEN** checkpoint status is aggregated
- **THEN** the result is `UNKNOWN` and exits non-zero
- **AND** no renderer or workflow converts it to pass.

#### Scenario: Ambiguous canonical state overlaps uncovered scope

- **GIVEN** a staged governed path appears uncovered while the canonical tip, predecessor chain, approval authority, or required Git identity is missing, stale, multiple, rolled back, forked, or ambiguous
- **WHEN** automatic checkpoint selection runs
- **THEN** canonical and Git validation runs first and returns `UNKNOWN` with exit one
- **AND** uncovered-path `FAIL` is not asserted until a single valid canonical seal and snapshot identity make coverage determinate.

### Requirement: Bounded checkpoint profiles

The module SHALL define cumulative `slice`, `commit`, and `deep` profiles whose selected obligations are derived from the sealed execution stages. `commit` SHALL include all applicable `slice` checks plus affected-component bounded targets. `deep` SHALL include all applicable lower-profile checks for its snapshot, bounded bug-hunt analysis, and every locally executable `prepush` obligation.

#### Scenario: Scope and profile are incompatible

- **GIVEN** a caller requests `--scope worktree --profile commit` or any scope/profile pair outside the allowed matrix
- **WHEN** checkpoint argument validation runs
- **THEN** the command rejects the request before Git extraction or evidence execution
- **AND** it neither evaluates worktree state as staged evidence nor silently switches to the index.

#### Scenario: Slice profile runs immediate semantic evidence

- **GIVEN** changed seal-relevant paths or inputs in any non-excluded role map to sealed `slice` obligations
- **WHEN** the slice profile runs
- **THEN** it verifies the seal and scope, runs the affected exact Requirements pytest cases, and imports changed-scope code-review evidence
- **AND** it does not run unrelated component or full-repository tests.

#### Scenario: Commit profile evaluates the staged index

- **GIVEN** exactly one policy-authorized canonical lineage-tip seal covers all staged non-excluded seal-relevant paths and `--scope index --profile commit` is selected
- **WHEN** the commit profile runs
- **THEN** it adds every affected component's bounded pytest targets and current-run JUnit evidence
- **AND** execution is bound to the captured index capsule rather than a differing worktree.

#### Scenario: Deep profile encounters CI-only obligation

- **GIVEN** a sealed obligation has earliest stage `ci`
- **WHEN** the deep local profile runs
- **THEN** the obligation is reported as deferred with identity and reason
- **AND** it is not described as locally passed or missing.

#### Scenario: Deep profile executes local pre-push assurance

- **GIVEN** the selected snapshot has applicable slice and affected-component checks, bounded bug-hunt analysis, and locally executable `prepush` obligations
- **WHEN** the deep profile runs
- **THEN** it executes the applicable lower-profile checks, bounded bug-hunt, and every locally executable `prepush` obligation
- **AND** missing or non-passing required evidence is aggregated through the released core result semantics rather than skipped or deferred.

### Requirement: Complete implementation scope evidence

The runtime SHALL reuse C14 worktree/index/range primitives and implement the released core snapshot matrix without guessing or lossy path parsing. Every snapshot base SHALL equal the seal-bound implementation-lineage origin repository/base commit/base tree. Worktree snapshots SHALL additionally bind a worktree-manifest digest and include staged, unstaged, and untracked state. Index snapshots SHALL additionally bind the exact index tree ID and exclude untracked paths unless staged as additions. Range snapshots SHALL bind full head commit/tree, policy-authorized current delivery-target commit/tree, plus origin-to-head ancestry and SHALL NOT represent untracked paths. Every manifest SHALL preserve additions, deletions, both rename endpoints, before/after modes, symlink target identity, and byte-preserving path identity; rename interpretation SHALL be bound to producer, policy, and toolchain identity. For every affected governed path that repository policy classifies as capable of defining a public interface, regardless of whether its role is `source`, `test`, `docs`, `generated`, or `evidence`, the runtime SHALL extract or import normalized base/current public-interface records using the released core snapshot schema. A side that does not exist by construction for an addition, deletion, or rename endpoint SHALL be represented by a normalized `absent` record/tombstone, not omitted. The tombstone SHALL bind the same path, role, exact snapshot, extractor identity/version/configuration, policy/toolchain, and Git-transition provenance required of a present observation and SHALL contain no fabricated interface members. Comparison of `absent` with `present` SHALL deterministically derive interface additions/removals, including both rename endpoints; an omitted record, unverifiable absence, or `absent` record for an existing path remains `UNKNOWN`. Base/current records SHALL otherwise bind extractor identity/version/configuration digest, policy/toolchain identity, path, role, and exact base/current snapshot provenance; changed-interface identities SHALL be derived by deterministic comparison rather than accepted as a caller-supplied set.

#### Scenario: Repository contains difficult path transitions

- **GIVEN** a change adds, deletes, renames, changes mode, symlinks, or uses quoted, Unicode, or trailing-character paths
- **WHEN** the implementation snapshot is extracted
- **THEN** every path and both rename endpoints are preserved with exact transition identity
- **AND** unresolved Git evidence yields `UNKNOWN`.

#### Scenario: Interface-capable path is added, deleted, or renamed

- **GIVEN** one side of an interface-capable path or rename endpoint does not exist in the exact base/current snapshot
- **WHEN** public-interface observations are normalized
- **THEN** the nonexistent side is a provenance-bound `absent` tombstone and the existing side is a provenance-bound `present` record
- **AND** their deterministic comparison derives the interface addition/removal instead of treating expected absence as missing evidence.

#### Scenario: Public-interface delta cannot be established

- **GIVEN** an affected governed path in any role can define a public interface but its base/current interface records are missing, unsupported, incomplete, stale, ambiguously normalized, or bound to a different snapshot or extractor configuration
- **WHEN** implementation scope evidence is assembled
- **THEN** changed-interface discovery is `unverifiable` and the checkpoint or conformance result is `UNKNOWN`
- **AND** an empty caller-supplied changed-interface set cannot close or omit interface obligations.

#### Scenario: Generated path defines a public interface

- **GIVEN** an affected governed path is classified as `generated` and repository policy classifies it as capable of defining a public interface
- **WHEN** checkpoint or conform extracts the snapshot-bound interface delta
- **THEN** the same complete base/current observations and extractor provenance required for any interface-capable role are enforced
- **AND** missing or unverifiable observations return `UNKNOWN` rather than an empty changed-interface set.

### Requirement: Seal-bound semantic evidence selection

The runtime SHALL classify every changed non-excluded seal-relevant path, public-interface record, and input in the selected worktree/index scope across `source`, `test`, `docs`, `generated`, and `evidence` roles plus seal-bound approval, test, dependency, policy, toolchain, and relevant configuration inputs. Approval-state discovery SHALL compare the authoritative base with the selected worktree/index snapshot so deletion, relocation, or replacement of the last seal or canonical lineage-tip artifact cannot be reclassified as a never-sealed repository. The runtime SHALL map each applicable path, changed-interface identity, and input through the sealed ownership and influence relationships to the corresponding risk rows, Requirements plan identities, exact pytest cases, bounded component targets, review/evidence obligations, and execution stages. A checkpoint MAY select only the affected subset of requirement, scenario, verification-case, and exact pytest-selector identities already bound by the seal; any addition, removal, replacement, or change of a bound identity SHALL require preflight validation, approval, and a new seal. Before intentional expansion can receive successor approval or failing-first evidence, any already-implemented out-of-scope production delta SHALL be removed from the selected implementation snapshot. The successor contract and tests SHALL then be authored and approved, failing-first evidence SHALL be captured against that expanded contract with the production behavior absent, and only then MAY the production expansion be reimplemented. The runtime and bundled workflow SHALL report and stop; they SHALL NOT automatically remove code, rewrite history, approve, or reseal. A non-excluded changed path or input MAY produce a determinate empty semantic-selector set only when the current valid canonical seal binds an explicit no-impact disposition for that exact input identity and role with a non-empty rationale. The result SHALL retain the disposition identity/digest and validation evidence; no-impact SHALL NOT suppress seal, scope, interface-discovery, or approval-state checks. If a seal-relevant changed path/interface/input or the obligations it can affect cannot be derived deterministically, or a claimed no-impact disposition is missing, stale, ambiguous, or mismatched, selection SHALL return `UNKNOWN` rather than an unproven empty set.

#### Scenario: Production path lacks semantic ownership

- **GIVEN** a changed production path has no sealed component or required semantic evidence mapping
- **WHEN** checkpoint selection runs
- **THEN** the result is `UNKNOWN`
- **AND** overall pytest success cannot satisfy the missing obligation.

#### Scenario: Test or execution input changes without source changes

- **GIVEN** only a sealed test, pytest configuration, dependency, policy, toolchain, generated/evidence path, or other relevant execution input changes
- **WHEN** checkpoint selection runs
- **THEN** the runtime selects every corresponding sealed case, target, review, and evidence obligation through the approved influence mapping
- **AND** an absent or ambiguous mapping returns `UNKNOWN` rather than an empty affected set or `NOT_APPLICABLE`.

#### Scenario: Changed input has an approved no-impact disposition

- **GIVEN** the canonical valid seal binds an explicit no-impact disposition with a non-empty rationale to the exact changed input identity and role
- **WHEN** semantic evidence selection runs
- **THEN** the runtime records the disposition identity, digest, rationale, and validation evidence and derives a determinate empty semantic-selector set for that input
- **AND** it still performs seal, scope, approval-state, and applicable interface-discovery checks rather than treating the change as unrelated.

#### Scenario: No-impact disposition cannot be verified

- **GIVEN** a changed input has no influence mapping and its claimed no-impact disposition is missing, stale, ambiguous, bound to another input or role, or lacks a non-empty rationale
- **WHEN** semantic evidence selection runs
- **THEN** the result is `UNKNOWN`
- **AND** an empty affected set cannot be inferred from the absence of a mapping.

#### Scenario: Implementation exceeds sealed scope

- **GIVEN** a changed path or behavior lies outside sealed roles and exclusions
- **WHEN** checkpoint comparison runs
- **THEN** it returns an `unexpected` failure and a `return_to_preflight` remediation class
- **AND** the already-implemented out-of-scope production delta is removed from the selected implementation snapshot before successor-contract approval and failing-first evidence
- **AND** intentional expansion is reimplemented only after the successor preflight review/seal and failing-first evidence, while preserving the original implementation-lineage origin baseline.

### Requirement: Current-run pytest and code-review evidence

The runtime SHALL first supply the upstream design contract, validation result, seal, policy, and current source identities to released core verification, then reuse existing Requirements pytest/JUnit and SpecFact code-review JSON contracts with exact producer and snapshot identities. It SHALL use released core finding precedence and deterministic `FAIL`/`UNKNOWN`/`PASS` aggregation rather than redefining them.

#### Scenario: Selector is missing, duplicate, uncollected, failed, or stale

- **GIVEN** required pytest evidence cannot be reconciled exactly to the selected snapshot and plan
- **WHEN** checkpoint evidence is normalized
- **THEN** the result is `FAIL` for a determinate violation or `UNKNOWN` for unresolved provenance
- **AND** no alternate selector grammar or historical overall exit code is accepted.

#### Scenario: Cache identity changes

- **GIVEN** the seal, snapshot, obligation set, pytest targets, runner, policy, toolchain, attested execution-environment/dependency state, allowlisted relevant environment, or relevant configuration changes
- **WHEN** cached evidence is considered
- **THEN** the prior cache entry is rejected
- **AND** required checks execute again.

#### Scenario: Execution environment cannot be attested

- **GIVEN** the active Python environment or a policy-allowlisted relevant environment variable cannot be deterministically identified without exposing secret values
- **WHEN** cached evidence is considered
- **THEN** cache reuse is disabled for that checkpoint
- **AND** the runtime reruns required checks, or returns `UNKNOWN` if the required execution itself cannot be performed.

### Requirement: Local and range authority separation

The runtime SHALL preserve core checkpoint authority for worktree/index results and SHALL require repository identity, the seal-bound implementation-lineage origin commit/tree, full immutable head commit/tree, a policy-authorized current delivery-target commit/tree identity, and origin-to-head ancestry for `specfact preflight conform <change-id>`. Tree attestations and the complete path manifest SHALL bind to that exact repository and cumulative lineage-origin-to-current-delivery-head range across all successor seals.

#### Scenario: Local pass is presented as PR proof

- **GIVEN** a worktree or index checkpoint passed
- **WHEN** a consumer requests final or protected PR authority
- **THEN** the runtime rejects promotion
- **AND** requires a new immutable-range conformance or protected consumer run.

### Requirement: Immutable-range conformance evaluation

`specfact preflight conform <change-id>` SHALL discover the policy-authorized canonical lineage tip from the canonical approval source; verify the supplied design contract, validation result, selected seal, policy, current source identities, implementation-lineage identity, immutable origin repository/base commit/base tree, and complete predecessor-seal chain; require the selected seal digest/monotonic sequence and chain digest to equal the canonical tip; require the range base to equal the lineage origin rather than a later successor-seal source snapshot; use C14 to prove that the full head descends from the origin and to extract the complete immutable lineage-origin-to-head manifest and range-bound evidence; extract or import snapshot-bound base/head public-interface records through the policy-authorized extractor and derive their complete changed-interface set; require the range head commit/tree to equal a policy-authorized current delivery-target identity resolved from the current local delivery ref/HEAD or supplied by an authenticated protected-PR/CI orchestrator; derive the deterministic exhaustive final-delivery obligation set; and invoke the released core implementation-assurance verifier. The exhaustive set SHALL include every changed governed path/interface and every applicable sealed component, acceptance criterion, risk row, Requirements verification case, component target, verification stage including `ci`, exclusion, and no-impact disposition in their transitive obligation closure. The set and its digest SHALL be bound to the result. A verified exact-input no-impact disposition MAY close that input with no influenced selectors, but its identity, digest, rationale, and validation evidence SHALL remain in the exhaustive closure. Missing, unsupported, incomplete, stale, ambiguous, wrong-snapshot, or wrong-extractor interface evidence SHALL keep conformance `UNKNOWN`; a caller cannot provide an empty interface set to shrink the closure. For an obligation whose earliest stage is `ci`, the runtime SHALL accept satisfaction only from a seal/policy-authorized protected-CI producer whose authenticated provenance is bound to the exact immutable range. Missing, local, self-asserted, unauthenticated, or wrong-range CI evidence SHALL remain `UNKNOWN`/deferred and SHALL prevent `PASS`. Human and JSON output SHALL preserve the core result status, findings, authority, evidence identities, and assurance limits without converting a non-passing outcome.

#### Scenario: Caller supplies an ancestor seal

- **GIVEN** an older seal and its predecessor chain are internally valid but the canonical approval source identifies a later approved successor as the current lineage tip
- **WHEN** checkpoint selection or final conformance runs
- **THEN** the selected-seal/tip mismatch is `stale` and returns `UNKNOWN`
- **AND** obligations introduced by the successor cannot be omitted by selecting the ancestor.

#### Scenario: Canonical seal tip is unavailable or ambiguous

- **GIVEN** the canonical approval source or its lineage-tip/chain/authority identity is missing, stale, rolled back, forked, or ambiguous
- **WHEN** checkpoint selection or final conformance runs
- **THEN** the result is `UNKNOWN` and exits non-zero
- **AND** the runtime does not guess the latest seal from timestamps or caller ordering.

#### Scenario: Final range is evaluated against the seal

- **GIVEN** a canonical latest valid seal and explicit repository, implementation-lineage origin commit/tree, full head commit/tree equal to the policy-authorized current delivery target, and origin-to-head ancestry identities
- **WHEN** final conformance runs
- **THEN** the runtime verifies upstream identities, extracts the exact immutable-range manifest and evidence, maps sealed final-delivery obligations, and invokes the core comparator
- **AND** the result remains independent from prior local checkpoint authority and protected PR review.

#### Scenario: Final obligation selection is incomplete

- **GIVEN** an immutable range affects one or more sealed paths, interfaces, behaviors, components, acceptance criteria, risk rows, Requirements cases, targets, stages, or exclusions
- **WHEN** final conformance omits, duplicates, or cannot deterministically resolve any member of the exhaustive transitive obligation closure, or selects an empty set for that affected range
- **THEN** the result is `UNKNOWN` with the incomplete selection identities
- **AND** comparison cannot pass until the complete result-bound obligation set is available.

#### Scenario: Caller attempts a truncated final range

- **GIVEN** implementation changes exist after the first seal's implementation-lineage origin baseline, including changes retained across successor seals
- **WHEN** a caller supplies a later range base, a different base tree, or a head without valid ancestry from the lineage origin
- **THEN** conform returns the released core `stale` or `unverifiable` finding and `UNKNOWN`
- **AND** it does not extract or compare a current-seal or caller-selected shorter range.

#### Scenario: Caller supplies an older descendant head

- **GIVEN** the requested range head descends from the lineage origin but differs from the policy-authorized current delivery-target commit or tree identity
- **WHEN** conform validates the immutable range
- **THEN** the head mismatch is `stale`, conform returns `UNKNOWN`, and the command exits non-zero
- **AND** later delivery commits cannot remain outside the evaluated manifest and obligation closure.

#### Scenario: CI-only final obligation has no protected evidence

- **GIVEN** the exhaustive final range closure contains an applicable obligation whose earliest stage is `ci`
- **WHEN** conform runs without authenticated evidence from an authorized protected-CI producer bound to that exact range
- **THEN** the obligation remains deferred with an `unverifiable` finding and `UNKNOWN`
- **AND** local or caller-constructed evidence cannot make final conformance pass.

#### Scenario: Final range comparison cannot be completed or does not conform

- **GIVEN** a stale or mismatched seal, unresolved range identity, unavailable required range-bound evidence, or a blocking core comparison finding
- **WHEN** final conformance is aggregated and rendered
- **THEN** the exact core `UNKNOWN` or `FAIL` outcome and findings are preserved
- **AND** the runtime cannot synthesize `PASS` from immutable references, prior local evidence, or overall test exit status alone.

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

The first rollout SHALL measure checkpoint behavior in shadow mode and SHALL exercise both accepted defect fixtures and representative known-green controls. Every corpus result and live observation SHALL bind the exact candidate implementation commit/tree and runtime/module identity, release-surface, policy, relevant configuration, corpus, runner, and toolchain digests. Any promotion-relevant identity change, including release preparation, SHALL invalidate the affected evidence and require recollection; evidence from an older candidate SHALL NOT authorize blocking for changed behavior. Blocking SHALL remain disabled until every corpus case produces its predeclared status, authority, finding set, and exit behavior; the exact current candidate's corpus has zero false PASS, zero false block, and no destructive/ambiguous behavior; and its live shadow observations meet a rollout-policy threshold declared before collection. The default threshold SHALL require at least 20 applicable known-good observations for each enabled scope/profile pair and at least 100 in aggregate, with both each pair's false-block rate and the aggregate rate no greater than 1%. Repository policy MAY require a larger per-pair or aggregate sample or lower rate but SHALL NOT weaken those defaults.

#### Scenario: C14 regression fixture is exercised

- **GIVEN** an accepted fixture represents an illegal exit, cache identity drift, malformed input, deletion-only change, difficult path, suppression relocation, or FAIL/UNKNOWN precedence defect
- **WHEN** slice or commit checkpoint dogfood runs
- **THEN** the defect is non-passing before simulated PR delivery
- **AND** duration, local detection, cycles, packet size, repeated class, and later-review outcome are recorded.

#### Scenario: Known-green control is exercised

- **GIVEN** a valid sealed fixture has complete scope, interface, ownership, selectors, evidence, and cache identity for an enabled scope/profile pair
- **WHEN** checkpoint dogfood runs
- **THEN** it produces the predeclared passing status, local authority, empty blocking-finding set, and exit zero
- **AND** a blanket `FAIL` or `UNKNOWN` implementation is recorded as a false block and cannot enable blocking.

#### Scenario: Pairwise shadow sample is too small or false-blocking exceeds policy

- **GIVEN** an enabled scope/profile pair has fewer than 20 applicable known-good observations, the aggregate has fewer than 100, a pairwise or aggregate observed false-block rate exceeds 1%, or any corpus expectation is mismatched
- **WHEN** rollout promotion is evaluated
- **THEN** seal-aware blocking remains disabled and shadow measurement continues
- **AND** one high-volume passing pair cannot hide an under-sampled or false-blocking pair.

#### Scenario: Candidate changes after shadow evidence is collected

- **GIVEN** corpus or live observations were collected for one candidate identity
- **AND** implementation, runtime/module, release-surface, policy, relevant configuration, corpus, runner, or toolchain identity changes before promotion
- **WHEN** rollout promotion is evaluated
- **THEN** the affected evidence is invalid for the changed candidate and cannot contribute to its thresholds
- **AND** shadow observations are recollected and all promotion gates are reevaluated against the exact current identity.

### Requirement: Signed publication before adapter consumption

After the implementation PR is merged to `dev`, the canonical post-merge publication workflow SHALL generate/version, sign, verify, compatibility-test, and propose one immutable #434 module release identity whose signed manifest separately binds the existing preflight workflow identity/digest and the new implementation-check workflow identity/digest. The proposal SHALL set the complete `core_compatibility` range identically in the bundle manifest and registry entry. Its lower bound SHALL identify the first released core containing the final #684 interfaces. Its exclusive upper bound SHALL be preserved from, or deterministically derived from, the intersection of the complete bundled-module dependency graph and SHALL NOT be omitted or widened past any required dependency's supported range. A core below the lower bound, at the upper bound, or above the upper bound SHALL be rejected; the exact lower bound and supported newer cores strictly below the upper bound SHALL pass the compatibility matrix. Neither a feature-branch artifact nor a merely proposed post-merge artifact is published or eligible for downstream handoff. Only after the publication PR is reviewed and merged and official registry/install readback passes SHALL the #434 identity be considered published and handed to core #251. Core #253 SHALL follow completed #251, and modules #433 SHALL consume the identities only after both #251 and #253 complete.

#### Scenario: Implementation branch prepares publication inputs

- **GIVEN** the #434 implementation PR has not merged to `dev`
- **WHEN** its release-surface matrix validates proposed manifest and compatibility metadata
- **THEN** it compares the proposed manifest with a projected registry row without mutating the official registry
- **AND** actual registry generation and manifest/registry equality verification remain exclusive to the canonical post-merge publication PR.

#### Scenario: Installation uses a core older than implementation assurance

- **GIVEN** the #434 module is resolved with a core identity below the manifest/registry `core_compatibility` lower bound containing #684
- **WHEN** compatibility or installation validation runs
- **THEN** the combination is rejected before checkpoint or conform execution
- **AND** manifest and registry metadata cannot advertise an unusable older core.

#### Scenario: Installation reaches a dependency-backed upper bound

- **GIVEN** one or more required bundled modules impose an exclusive upper core-compatibility bound
- **WHEN** the #434 manifest and projected or generated registry entry are prepared or compatibility-tested
- **THEN** both surfaces carry the same upper bound derived from the complete dependency intersection
- **AND** the matrix accepts supported cores below it and rejects the bound itself plus a representative core above it.

#### Scenario: Adapter requests the new workflow

- **GIVEN** the #434 implementation and canonical publication PRs are merged, matching complete manifest/registry `core_compatibility` ranges and their lower/upper-bound matrix pass, official registry/install readback passes, and core #251 then #253 are complete
- **AND** #433 prepares a harness adapter
- **WHEN** it resolves the canonical module and workflow identities
- **THEN** it consumes the exact signed #434 module identity, preflight workflow identity/digest, and implementation-check workflow identity/digest
- **AND** #434 contains no harness-specific adapter package.
