## ADDED Requirements

### Requirement: Explicit Review Scope Evidence

`specfact code review run` SHALL support unambiguous `worktree`, `index`, `range`, and `full` scopes plus explicit positional files. Range SHALL accept optional `--pr-context-file <absolute-path>` as claimed event context. A structurally valid matching file yields producer `assurance_kind=range_candidate`; absence yields `range_preview`. The producer SHALL never emit or self-assert `pr_range`. Index scope SHALL analyze the exact staged blob snapshot, not current worktree path content. Range scope SHALL require base and head refs, resolve full base/head and merge-base commit/tree SHAs, select the committed merge-base-to-head delta, and use the merge-base—not the supplied base-ref tip—as the differential baseline. Changed tests SHALL be included. A complete range with valid matching claimed context SHALL emit `assurance_kind=range_candidate`; the same complete local selection without context SHALL emit `assurance_kind=range_preview`. Neither producer value alone satisfies a PR-assurance consumer. Range SHALL reject `--exclude-tests`, every `--focus` facet, `--path`, `--no-tests`, and `--level` before analysis; this change defines no filtered-range assurance. `changed` SHALL be a deprecated alias for `worktree`, not PR range. Positional files SHALL emit `assurance_kind=explicit_files` and SHALL NOT satisfy a consumer or policy requiring `pr_range` assurance.

For index mode, `scope.py` SHALL write and materialize the complete Git index tree outside the caller worktree: staged entries provide changed bytes while all unchanged tracked entries retain their HEAD/index bytes. Only the staged governed selection is reviewed, but imports/config/support reads resolve from this complete isolated index root. The report SHALL distinguish selected staged paths from supporting tree paths and bind the index tree plus full path/blob/content manifest digest. Later unstaged or untracked caller-worktree bytes cannot affect analysis. For range mode, it SHALL materialize fresh detached merge-base/head roots from the resolved commit trees outside the caller worktree plus a separate sealed policy bundle from the resolved target base-ref tip. For PR assurance, the protected pull-request/merge-queue workflow SHALL create immediately before invocation an immutable canonical JSON `--pr-context-file` outside the checkout and every materialized source/policy root. Its `github-actions-pr-v1` record contains provider, repository ID/name, target ref, pull-request or merge-queue identity, expected full target-tip commit SHA/tree SHA, expected head commit/tree, event identity/digest, and schema version. The resolver rejects a symlink/non-regular/in-root file, freezes its bytes/digest before analyzer execution, and does not let analyzed code rewrite the in-memory identity. The producer SHALL derive `expected_target_tip` only from that record. It SHALL resolve the supplied base ref and require its commit/tree to equal that authenticated expectation before freezing policy; a caller-supplied ref or self-asserted expectation alone is not trusted. The report SHALL bind the trusted-context digest plus expected and resolved target identities. A moved, mismatched, untrusted, missing, or unreadable target identity or policy SHALL yield UNKNOWN. The producer treats every context file as claimed provenance and emits only `range_candidate` after structural and identity checks; it has no producer-verifiable trust signal. Range without a valid context file emits `range_preview`. A protected consumer SHALL independently derive the expected merge base and complete governed merge-base-to-head diff from workflow-native target/head identities. Under the protected policy it SHALL recompute the sorted governed selected-file and selected-line manifests, diff digest, status/rename/deletion facts and digests; resolve the authorized target-tip policy/config identity; require the approved signed producer module/schema/profile/analyzer-toolchain identities; verify producer workflow/ref/run/attempt/job plus report-artifact identity/digest; and compare every value with the immutable producer report. On success it emits a separate verification envelope binding producer report digest, trusted event digest, repository/PR-or-queue/target/head identities, analyzed merge-base commit/tree, governed diff/selection/line/status/rename/deletion manifests and digests, selected policy/config source/package/version/commit/tree/blob/content/config digests as applicable, approved producer module/schema/profile/toolchain identities, producer workflow/ref/run/attempt/job/artifact identities, verifier workflow/ref/run/attempt identity, consumer policy version, decision, and `effective_assurance_kind=pr_range`. Any missing governed input or merge-base, diff, selection, manifest, policy/config, producer, or artifact mismatch emits rejection/UNKNOWN. The consumer verifies selection and provenance; it does not independently re-run analyzers or claim to verify finding semantics. It SHALL NOT mutate the producer report, and no producer field or self-asserted context file alone satisfies a `pr_range` policy. The merge-base remains the source-code baseline, while the current authorized target-tip policy governs both source snapshots. The resolver SHALL manifest each selected analyzer input and declared analyzer-config input with the closed tagged `AnalyzerInputIdentity` union `git_blob | signed_module_payload | generated_projection | builtin_mode`. `git_blob` binds repository/commit/tree/path/blob/content digests; `signed_module_payload` binds signed module name/version/checksum/signature/canonical path/content digest; `generated_projection` binds generator identity/schema, parent identity/digest, logical transform/root-substitution digest, and output digest; `builtin_mode` binds analyzer/tool version plus exact mode/argv and has no file. Only `git_blob` may populate a reviewed-repository blob field. Every materialized file also binds its output SHA-256, and producer plus protected consumer SHALL canonicalize and validate the same tagged representation; pass only materialized-root paths to analyzers; pass explicit target-policy config paths to configurable adapters; and verify every snapshot manifest before and after analysis. Ruff SHALL use explicit target-policy `--config` or `--isolated`, Pylint explicit target-policy `--rcfile` or a sealed pinned-default config, basedpyright an explicit per-snapshot projected `--project` rather than `.` or the policy-bundle config path, and Semgrep an explicit `bundle_root` containing either the authorized target-tip clean-code policy or the contract-named sealed clean-code fallback from the exact signed installed Code Review module. For basedpyright, the pinned configuration schema SHALL identify every filesystem path field (including nested execution environments); source-relative values SHALL be rewritten to the corresponding merge-base or head materialization, and `venvPath`/`venv` SHALL resolve to the same sealed toolchain environment for both sides. The original policy digest, projection mapping/digest, and resulting absolute roots SHALL be recorded. Unsupported path semantics, path escape, a path into the target-policy bundle/caller worktree, or a missing projected dependency SHALL yield UNKNOWN. Every index or range snapshot analyzer execution SHALL consume one manifest-bound `SnapshotInvocationContext` containing the snapshot commit/tree/root, exact working directory, allowed import roots, sealed toolchain executable/environment identity, sanitized environment, process-private output/temp roots, sandbox backend/capability identity, and context digest. Each subprocess SHALL run with `cwd` equal to its materialized index or range source root. The environment SHALL remove caller/worktree/policy-bundle import paths and inherited `PYTHONPATH`, `PYTHONHOME`, editable-source roots, user-site and startup hooks; then add only declared snapshot import roots plus the same sealed non-editable toolchain/dependency environment. Targeted pytest SHALL disable automatic third-party plugin loading and enable only pinned declared plugins. Pylint init hooks, CrossHair imports, targeted pytest collection/execution, and any other import-capable analyzer SHALL therefore resolve repository modules only from the active snapshot. Environment sanitization alone is insufficient. Every analyzer process SHALL run inside a fresh OS-enforced deny-by-default filesystem sandbox. The only initial accepted profile is `linux-bwrap-v1`, using the exact sealed-toolchain Bubblewrap executable and binding its SHA-256, version, argv/profile schema, and capability-probe digest; another OS/backend, missing executable, or failed namespace/mount/network probe yields UNKNOWN. The sandbox exposes only its active snapshot read-only, exact selected/projected config and sealed toolchain/dependency inputs read-only, and its own empty output/temp/cache/home roots writable. The caller checkout, opposite snapshot, claimed/trusted context, target-policy or fallback source roots beyond the selected projected payload, controller/report state, sibling analyzer outputs, host credentials, and network SHALL be absent or denied; undeclared file descriptors SHALL be closed. The trusted controller outside the sandbox SHALL capture argv plus OS-observed exit/stdout/stderr, accept artifacts only from that process-private output root after exit, validate declared shape/digests and all source/config manifests, classify them as `candidate_executed_observation`, and seal those exact bytes before dependent comparison. That seal proves post-collection immutability, not that candidate Python could not influence its own process or process-private artifact. The report SHALL bind sandbox backend/version, capability-probe result, mount/permission/network profile, and per-process root-manifest digest. Missing or failed isolation capability, denied-profile mismatch, cross-root access, unexpected output, or adapter unable to honor the context SHALL yield UNKNOWN; strict index/range assurance SHALL NOT fall back to an unsandboxed process. Adapter/config injection failure SHALL yield UNKNOWN. Index and range modes SHALL reject `--fix`, `--preview-fixes`, and `--with-mutation`. Any index conflict/object failure, materialization failure, path-root violation, or content-integrity failure SHALL yield UNKNOWN.

The report SHALL record requested/effective scope, assurance kind, repository root, index tree/blob identities when applicable, supplied base/head refs and resolved commit/tree SHAs, authenticated expected target-tip commit/tree plus trusted-context digest, the analyzed merge-base commit/tree SHA, diff digest, selected files/lines and content manifests, rename/deletion facts, filters/facets, trusted policy/config identity and per-snapshot config-projection digests, sandbox backend/capability and per-process root-manifest digests, `runtime_trust_model`, `adversarial_runtime_evidence`, per-member observation trust, resolver identity, status, and diagnostics.

#### Scenario: Clean PR checkout still reviews committed range files

- **GIVEN** a clean checkout whose head contains committed changes relative to base
- **WHEN** range scope runs with those refs
- **THEN** the committed merge-base-to-head files, including tests, are reviewed
- **AND** worktree emptiness does not produce an empty PR review.

#### Scenario: PR range binds the authenticated expected target tip

- **GIVEN** a protected PR or merge-queue workflow writes the `github-actions-pr-v1` context file outside the checkout immediately before invocation
- **WHEN** range scope freezes that regular file and resolves the caller's base ref
- **THEN** the resolved base-tip and head commit/tree identities must exactly equal the authenticated expectations before policy is selected
- **AND** the report binds expected/resolved identities and the trusted-context digest
- **AND** mismatch, movement, or a self-asserted/untrusted expectation yields UNKNOWN
- **AND** the producer emits only range_candidate after its structural/identity checks and never claims pr_range
- **AND** the consuming PR gate independently matches the immutable report digest and those fields to workflow-native trusted event context
- **AND** only its separate digest-bound verification envelope may set `effective_assurance_kind=pr_range`
- **AND** missing context emits range_preview, while invalid/unsafe/mismatched context is UNKNOWN; neither producer state alone satisfies pr_range.

#### Scenario: Index analysis uses staged bytes, not later unstaged edits

- **GIVEN** a tracked pathname has staged content and different additional unstaged worktree edits
- **WHEN** index scope runs
- **THEN** scope.py writes and materializes the complete index tree, while the reviewed selection remains the staged governed paths
- **AND** analyzers receive the staged blob bytes and imports/config/support resolve only from HEAD-plus-index bytes under the isolated index root
- **AND** every subprocess consumes the index SnapshotInvocationContext rather than caller cwd/environment
- **AND** the unstaged bytes do not affect findings, score, or status
- **AND** the report binds selected paths separately from the complete index tree/path/blob/content manifest.

#### Scenario: Index imports use HEAD-plus-index dependencies

- **GIVEN** a staged module imports another tracked module whose index content differs from additional unstaged worktree edits
- **WHEN** an import-capable analyzer runs in index scope
- **THEN** the reviewed module and imported dependency come from the complete materialized index tree
- **AND** cwd, import roots, configuration, and outputs come from the index SnapshotInvocationContext
- **AND** caller-worktree dependency bytes cannot affect findings or status
- **AND** a missing tree object, manifest mismatch, or caller-source resolution yields UNKNOWN.

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
- **AND** no narrowed result carries `assurance_kind=range_candidate` or a consumer `effective_assurance_kind=pr_range`, or turns a non-empty governed range into NOT_APPLICABLE
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

Range enforcement SHALL analyze the resolved merge-base and head with identical shared analyzer/configuration identity: analyzer and toolchain identities; trusted target-policy/config source digest; projection algorithm/schema identity; and a canonical logical projection-map digest whose source-root placeholders are independent of either materialized path. Per-snapshot projected-config bytes and digests MAY differ because their absolute roots differ; those digests are materialization evidence and SHALL NOT be compared for raw equality. A mismatch in any shared identity field yields UNKNOWN, while a difference limited to the recorded side-specific root substitutions does not. The supplied base-ref tip SHALL NOT be used as the analyzer baseline when it differs from the merge base. Stable fingerprints SHALL classify findings as introduced, fixed, unchanged, or unknown. Before fingerprint comparison, the head file anchor for a resolved one-to-one rename SHALL be normalized to the recorded old/base path; copies and unpaired additions SHALL NOT be rename-normalized, and both original paths plus the rename fact SHALL remain in evidence. Changed-line intersection SHALL be evidence only and SHALL NOT be the sole introduction rule.

#### Scenario: Advanced base-ref tip does not replace the merge-base baseline

- **GIVEN** the target base-ref tip advanced after the feature head diverged
- **WHEN** range differential analysis runs
- **THEN** the baseline analyzer snapshot is the resolved merge-base SHA
- **AND** target-only changes after divergence are not classified as feature-branch fixes or introductions
- **AND** the supplied base-ref tip remains recorded as resolver evidence
- **AND** its commit/tree exactly matches the authenticated `expected_target_tip`
- **AND** its authorized target-tip policy/config bundle is applied identically to the merge-base and head source snapshots
- **AND** an untrusted, mismatched, moved, missing, or unusable target policy identity yields UNKNOWN.

#### Scenario: Pure rename preserves an unchanged finding

- **GIVEN** a one-to-one range rename moves a file without changing its bytes and the same blocker is reported at the old base path and new head path
- **WHEN** differential fingerprints are compared
- **THEN** the head anchor is normalized through the recorded rename relation to the old/base path
- **AND** the blocker is classified unchanged rather than fixed at base and introduced at head
- **AND** the report retains both paths and the rename fact.

#### Scenario: Candidate config cannot suppress its own finding

- **GIVEN** the head changes analyzer configuration to suppress a finding that the trusted target-base-tip policy would report
- **WHEN** merge-base and head snapshots are analyzed
- **THEN** every configurable adapter receives the same explicit sealed selected configuration for both sides: governed target-tip policy when present, or only a fallback expressly permitted by this contract
- **AND** no adapter discovers configuration from the merge-base source tree, head tree, caller worktree, or process current directory
- **AND** the head-side candidate configuration remains scope/shadow evidence but cannot change differential enforcement
- **AND** missing or unusable selected configuration yields UNKNOWN; absence MAY use only the named Ruff isolated mode, sealed Pylint default, or sealed Semgrep clean-code fallback, never discovery.

#### Scenario: Consumer without repository Semgrep policy uses the signed module fallback

- **GIVEN** the authorized target-tip policy bundle has no `.semgrep/clean_code.yaml`
- **WHEN** the mandatory `semgrep` profile member is planned
- **THEN** the resolver materializes the canonical clean-code policy payload from the exact installed, signed Code Review module artifact into a read-only bundle outside both source snapshots and the target-policy bundle
- **AND** the report binds `config_source=module_default`, module name/version/checksum/signature, canonical payload path, source blob/content digest, materialized-config digest, and the same selection for both sides
- **AND** Semgrep receives that bundle explicitly and cannot discover policy from an analyzed source tree, caller worktree, or process current directory
- **AND** missing, untrusted, version/checksum/signature-mismatched, or digest-mismatched fallback evidence yields UNKNOWN
- **AND** this clean-code fallback does not make `semgrep-bugs` applicable when the authorized target-tip bugs configuration is absent.

#### Scenario: basedpyright projects relative paths into each source snapshot

- **GIVEN** the trusted target policy contains relative basedpyright source/import paths
- **WHEN** merge-base and head analysis is prepared
- **THEN** the pinned configuration schema rewrites every source-relative path to the corresponding immutable source root
- **AND** environment fields resolve to the same sealed toolchain environment on both sides
- **AND** basedpyright receives a distinct manifest-bound projected `--project` artifact for each side, never the policy-bundle config path or process `.`
- **AND** an imported dependency is read from the appropriate merge-base or head snapshot
- **AND** unsupported, escaping, external, or missing projected paths yield UNKNOWN.

#### Scenario: Import-capable analyzers stay inside each materialized snapshot

- **GIVEN** an imported repository dependency has different content at merge base and head while caller/worktree source is also present
- **WHEN** Ruff, Radon, Pylint, basedpyright, either Semgrep pass, CrossHair, targeted pytest, or any other analyzer subprocess executes for each side
- **THEN** each process uses that side's materialized source root as `cwd`
- **AND** its sanitized import environment contains only manifest-bound snapshot roots and the same sealed non-editable toolchain/dependency environment
- **AND** pytest automatic plugin loading and caller/user startup paths are disabled
- **AND** every subprocess uses the sealed executable/cwd/environment/output context, and merge-base import-capable execution imports merge-base content while head execution imports head content
- **AND** caller/worktree/policy-bundle source resolution or invocation-context mismatch yields UNKNOWN.

#### Scenario: Analyzer sandbox denies cross-root evidence access

- **GIVEN** distinct caller, merge-base, head, context, policy-source, controller, and sibling-output roots contain unique sentinel files
- **WHEN** a synthetic import-capable analyzer, targeted pytest case, or CrossHair target attempts absolute, relative, symlink, descriptor, or network access outside its declared active snapshot and process-private output/temp roots
- **THEN** the OS sandbox denies every cross-root read and write and exposes no host credentials or network
- **AND** the active snapshot and exact selected config/toolchain inputs are read-only while only that process's empty output/temp/cache/home roots are writable
- **AND** the controller seals only validated artifacts from that process-private output after exit, before another analyzer or side runs
- **AND** the report binds `linux-bwrap-v1`, Bubblewrap executable/version/digest, argv/profile schema, capability probe, mount/permission/network profile, and root-manifest digest
- **AND** unsupported isolation, boundary escape, undeclared file descriptor, unexpected output, or profile mismatch yields UNKNOWN without unsandboxed retry.

#### Scenario: Runtime observations expose their adversarial trust boundary

- **GIVEN** targeted pytest, CrossHair, or another member executes candidate Python
- **WHEN** `pr-range-v1` records or consumes that member's result
- **THEN** the report labels its raw outputs `candidate_executed_observation`, binds `runtime_trust_model=candidate-not-intentionally-subverting-observer-v1`, and states `adversarial_runtime_evidence=false`
- **AND** controller sealing claims only exact post-collection bytes and cross-root isolation, never that candidate-authored assertions, exit behavior, or process-private artifacts are hostile-code-proof
- **AND** a protected consumer requiring adversarial-candidate-resistant runtime evidence receives UNKNOWN for every candidate-executing member and aggregate assurance cannot PASS
- **AND** no candidate-writable JUnit, coverage, stdout, or exit result is upgraded to a hostile-code attestation by digesting it.

#### Scenario: Analyzer identity mismatch is unknown

- **GIVEN** merge-base and head analyzer/toolchain, target-policy/config source, projection algorithm/schema, or canonical logical projection-map identities differ
- **WHEN** differential classification is requested
- **THEN** the affected comparison is UNKNOWN
- **AND** no finding is classified introduced, fixed, or unchanged from non-identical analyzer inputs
- **AND** strict enforcement exits non-zero with both shared identities and side-specific projected-config digests retained
- **AND** different projected bytes caused only by the recorded merge-base/head root substitutions do not create a false identity mismatch.

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

Strict PR-range assurance SHALL use the closed schema-versioned `pr-range-v1` profile defined authoritatively in `run/runner.py` and bound in the report by profile ID and policy/config digest. Required analyzer IDs are `ruff`, `radon`, `semgrep`, `ai-bloat-ast`, `ast-clean-code`, `basedpyright`, `pylint`, and `contracts`. The mandatory `semgrep` member SHALL use the authorized target-tip clean-code policy when present and otherwise the sealed clean-code fallback from the exact signed installed Code Review module; absence or integrity failure of both is UNKNOWN, not optional or NOT_APPLICABLE. `semgrep-bugs` is conditionally required when the trusted target-base-tip policy snapshot contains the governed bugs configuration; `targeted-pytest-coverage` is conditionally required when the complete range contains governed production Python or any governed Python test/test-support input. When the semgrep-bugs condition is absent its outcome SHALL be NOT_APPLICABLE rather than skipped. Targeted pytest is NOT_APPLICABLE only when the complete range contains neither governed production Python nor governed Python test/test-support input. The profile has no optional analyzers, and range cannot disable the targeted pytest member with `--no-tests`. This strict completeness is evaluated under `runtime_trust_model=candidate-not-intentionally-subverting-observer-v1`; the report and protected envelope SHALL carry `adversarial_runtime_evidence=false`. If consumer policy requires hostile-candidate-resistant runtime evidence, candidate-executing members and aggregate assurance are UNKNOWN rather than PASS.

The report SHALL list each profile member with required/conditional status; `execution_state=ran|error|not_applicable`; `evidence_outcome=PASS|FAIL|UNKNOWN|NOT_APPLICABLE`; per-snapshot version, toolchain and typed configuration/input identities/digests; duration; and diagnostics. `FAIL` is reserved for valid completed evidence that violates policy, including blocking analyzer findings and collected targeted-test assertion/skip/xfail/xpass outcomes. `UNKNOWN` is required for unavailable tools, launch errors, timeouts, unexpected process exits, parse errors, identity/config mismatch, missing artifacts, selector/count/JUnit/coverage reconciliation errors, or otherwise incomplete required execution. The generic term `failed` SHALL NOT collapse these states. Legacy verdict and exit fields derive only from aggregate authoritative `assurance_status`, so infrastructure UNKNOWN projects to non-shadow exit 1/legacy FAIL without becoming semantic FAIL. For every profile member, the planner SHALL derive eligible inputs independently for the merge-base and head from their immutable manifests. A side with zero eligible inputs MAY record NOT_APPLICABLE only with its snapshot commit/tree, input-class identity, empty eligible-input set, manifest digest, and `absence_reason=no_eligible_inputs_in_snapshot`; this is explicit coverage truth, not a skipped/missing analyzer. If any eligible input exists on that side, NOT_APPLICABLE is forbidden and unavailable, skipped-without-valid-semantic-test-evidence, launch/process-error, timed-out, unparsable, artifact/reconciliation-defective, or identity-mismatched required analysis SHALL make assurance UNKNOWN. A per-snapshot NOT_APPLICABLE result does not make the whole range NOT_APPLICABLE when the opposite side or the range contains governed Python. This rule covers add-only and delete-only ranges without allowing an adapter's unrecorded empty-file early return to count as success. Zero findings SHALL count as successful coverage only when an explicit successful run record exists; an empty finding list alone is not analyzer evidence. Targeted pytest coverage SHALL bind the exact planned test paths/selectors and selector digest; pytest/coverage versions; environment/config digest; JUnit digest; per-selector collected/passed/failed/skipped/xfailed/xpassed/deselected outcome; aggregate counts; per-snapshot outcome; and coverage artifact digest. For production changes, the planner SHALL compute and digest deterministic source-to-test plans independently at merge base and head, normalize selector file paths through the recorded one-to-one rename map, and form the effective head selector plan from the union of head-plan selectors, still-present baseline-plan selectors, and changed-test inventory selectors. For every deleted production input, each exact selector from its baseline source-to-test plan SHALL run against the head snapshot; a missing baseline plan, or a baseline selector that cannot be resolved and collected at head, SHALL yield `deleted_input_without_head_test_plan` UNKNOWN rather than NOT_APPLICABLE or PASS. Every changed or added collectable Python test file SHALL be collected independently at merge base and head; both sorted selector inventories and digests are evidence, and recorded one-to-one file renames normalize only the path portion before comparison. Every head selector is planned even when no production file changed. Each planned selector SHALL collect exactly once on every applicable side. Any normalized baseline selector absent from the head inventory is explicit `removed_selector` UNKNOWN evidence and blocks strict assurance; a head-only selector uses the manifest-bound baseline-absence rule and must pass at head. Function rename without an explicit stable selector identity remains one removal plus one addition and cannot silently PASS. A deleted changed test or changed test-support input that cannot be deterministically expanded to exact head selectors SHALL likewise yield UNKNOWN with deletion/selection diagnostics rather than NOT_APPLICABLE or PASS. Only an exact head-side set in which every selected test executes and passes MAY satisfy the member. A selected head test that is skipped, xfailed, or xpassed SHALL yield FAIL because it is not passing evidence; a missing, duplicate, or deselected selected test or a count/JUnit reconciliation mismatch SHALL yield UNKNOWN. It SHALL be evaluated separately for each snapshot. A valid baseline assertion/skip/xfail/xpass outcome remains per-snapshot FAIL evidence but SHALL NOT directly determine the range aggregate; when the same normalized selector collects exactly once and passes at head, the transition is `fixed` and non-blocking. Head-side non-passing evidence remains FAIL. A snapshot containing any governed production Python, Python test, or Python test-support input eligible for this member requires a valid targeted run. The general zero-eligible-input rule applies only when that side contains none of those three eligible input classes. In addition, the merge-base side MAY record NOT_APPLICABLE when immutable range evidence proves that every selector needed by the member is introduced after the merge base and therefore structurally absent there; this selector exception SHALL bind the absent paths/selectors and `absence_reason=not_present_at_merge_base`. These explicit absent-side results are neither skipped coverage nor no-tests-collected runs, and the aggregate member remains required on every side containing governed production Python, Python test, or Python test-support input. A head snapshot that still contains any such eligible input but has no selectable/collected tests is UNKNOWN; deletion or loss of head-side test coverage cannot use the baseline-selector-absence exception. Pytest unavailability, timeout, collection/internal/usage error, unexpected no-tests-collected, missing/duplicate/deselected selected tests, JUnit/count mismatch, or missing/unreadable coverage SHALL yield UNKNOWN; collected head assertion failures and selected head skip/xfail/xpass outcomes SHALL yield FAIL; an exact all-selected-passed run records ran/pass and its coverage findings. Analyzer adapters SHALL surface timeout, unavailable, parse, and documented tool/process-exit failures explicitly. The required `contracts` member includes the CrossHair subprocess; a CrossHair timeout or documented process-error exit (including exit code 2 with no parsed counterexample) SHALL record failed contracts coverage with exit/stderr diagnostics and make assurance UNKNOWN rather than returning an empty success. A successfully parsed CrossHair counterexample remains a contracts finding and SHALL NOT be relabelled as infrastructure uncertainty.

#### Scenario: Infrastructure errors remain distinct from failing evidence

- **GIVEN** one required member reports either a valid completed policy violation or an infrastructure/identity/reconciliation error
- **WHEN** per-member and aggregate statuses are derived
- **THEN** a blocking analyzer finding or valid head-side collected assertion/skip/xfail/xpass outcome records `execution_state=ran`, `evidence_outcome=FAIL`, and aggregate FAIL
- **AND** a baseline non-passing outcome remains per-snapshot FAIL evidence, but the same normalized selector passing at head is classified fixed and does not block
- **AND** unavailable, launch, timeout, unexpected-exit, parse, identity/config, missing-artifact, or reconciliation error records `execution_state=error`, `evidence_outcome=UNKNOWN`, and aggregate UNKNOWN
- **AND** both non-shadow aggregates exit 1 and may project legacy FAIL, but the authoritative statuses remain distinct.

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
- **THEN** the profile records the planned selector digest, exact per-selector JUnit outcomes/counts, runner/environment identities, JUnit digest, and coverage artifact digest
- **AND** only an exact head set where every selected test collects once, executes, and passes satisfies the member
- **AND** assertion failure or selected head skip/xfail/xpass produces FAIL
- **AND** unavailable pytest, timeout, collection/internal/usage error, unexpected no collected tests, missing/duplicate/deselected selected tests, reconciliation mismatch, or missing/unreadable coverage produces UNKNOWN
- **AND** only a manifest-proven absent-side input/selector produces NOT_APPLICABLE for that side
- **AND** the stage cannot be omitted by `--no-tests`.

#### Scenario: Delete-only production preserves baseline test intent at head

- **GIVEN** a range deletes governed production Python while its baseline source-to-test selectors still exist at head
- **WHEN** targeted pytest coverage plans the head side
- **THEN** the planner binds both source-to-test plan digests and includes every still-present baseline selector in the effective head selector union
- **AND** each such selector collects exactly once and executes against the head snapshot
- **AND** a missing baseline plan or selector that cannot be resolved and collected at head is `deleted_input_without_head_test_plan` UNKNOWN
- **AND** delete-only production cannot make the head member NOT_APPLICABLE merely because the deleted source is absent there.

#### Scenario: Repaired baseline test is fixed evidence

- **GIVEN** a normalized planned selector has a valid non-passing result at merge base and collects exactly once and passes at head
- **WHEN** targeted pytest evidence is aggregated
- **THEN** the baseline result remains per-snapshot FAIL evidence
- **AND** the pair is classified `fixed` and is non-blocking
- **AND** the baseline failure does not override the exact passing head result or force aggregate FAIL
- **AND** infrastructure or selector-reconciliation uncertainty on either side remains UNKNOWN.

#### Scenario: Test-only Python range executes changed tests

- **GIVEN** a range changes or adds governed Python tests without changing production Python
- **WHEN** targeted pytest coverage plans the head side
- **THEN** it records and digests merge-base and head selector inventories for every changed/additional collectable test file
- **AND** it normalizes selector file paths through recorded one-to-one renames, executes every head selector, and reconciles the set difference
- **AND** a failing changed-test assertion yields FAIL even when static analyzers are clean
- **AND** any baseline selector missing at head, deleted test, or changed test-support input without deterministic exact head selectors yields UNKNOWN
- **AND** the member is never NOT_APPLICABLE merely because production Python did not change.

#### Scenario: Head cannot neutralize selected tests with pytest outcomes

- **GIVEN** a planned head selector is changed to skip, xfail, xpass, or become deselected
- **WHEN** targeted pytest coverage reconciles the exact selector set with JUnit
- **THEN** skip, xfail, or xpass is FAIL rather than passing coverage
- **AND** deselected, missing, duplicate, or count-mismatched selectors are UNKNOWN
- **AND** an exit-zero pytest process and readable coverage artifact cannot override those outcomes
- **AND** only exactly-once collected and passed selectors satisfy the head member.

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

