## ADDED Requirements

### Requirement: Explicit Review Scope Evidence

`specfact code review run` SHALL support unambiguous `worktree`, `index`, `range`, and `full` scopes plus explicit positional files. Range SHALL accept optional `--pr-context-file <absolute-path>` as claimed event context. A structurally valid matching file yields producer `assurance_kind=range_candidate`; absence yields `range_preview`. The producer SHALL never emit or self-assert `pr_range`. Index scope SHALL analyze the exact staged blob snapshot, not current worktree path content. Range scope SHALL require base and head refs, resolve full base/head commit/tree SHAs, enumerate all best merge bases, require exactly one resolved merge-base commit/tree, select that committed merge-base-to-head delta, and use the unique merge base—not the supplied base-ref tip—as the differential baseline. Zero or multiple best merge bases is UNKNOWN; this change defines no virtual-base algorithm. Changed tests SHALL be included. Governed impact SHALL include Python source/test/test-support inputs and the closed `governed-policy-paths-v1` analyzer/test/coverage-policy inputs plus every authenticated target-tip project-runtime `source_lock_paths[]` member; a policy-only governed range is never NOT_APPLICABLE. A complete range with valid matching claimed context SHALL emit `assurance_kind=range_candidate`; the same complete local selection without context SHALL emit `assurance_kind=range_preview`. Neither producer value alone satisfies a PR-assurance consumer. Range SHALL reject `--exclude-tests`, every `--focus` facet, `--path`, `--no-tests`, and `--level` before analysis; this change defines no filtered-range assurance. `changed` SHALL be a deprecated alias for `worktree`, not PR range. Positional files SHALL emit `assurance_kind=explicit_files` and SHALL NOT satisfy a consumer or policy requiring `pr_range` assurance.

For index mode, `scope.py` SHALL write and materialize the complete Git index tree outside the caller worktree: staged entries provide changed bytes while all unchanged tracked entries retain their HEAD/index bytes. Only the staged governed selection is reviewed, but imports/config/support reads resolve from this complete isolated index root. The report SHALL distinguish selected staged paths from supporting tree paths and bind the index tree plus full path/object-type/Git-mode/blob/content manifest digest. Later unstaged or untracked caller-worktree bytes cannot affect analysis. For range mode, it SHALL materialize fresh detached merge-base/head roots from the resolved commit trees outside the caller worktree plus a separate sealed policy bundle from the resolved target base-ref tip. For PR assurance, the protected pull-request/merge-queue workflow SHALL create immediately before invocation an immutable canonical JSON `--pr-context-file` outside the checkout and every materialized source/policy root. Its `github-actions-pr-v1` record contains provider, repository ID/name, target ref, pull-request or merge-queue identity, expected full target-tip commit SHA/tree SHA, expected head commit/tree, event identity/digest, schema version, and, when an import-capable member is applicable, the complete `project-runtime-layer-v1` descriptor/build attestation plus canonical digest. The resolver rejects a symlink/non-regular/in-root file, freezes its bytes/digest before analyzer execution, and does not let analyzed code rewrite the in-memory identity. The producer SHALL derive `expected_target_tip` only from that record. It SHALL resolve the supplied base ref and require its commit/tree to equal that authenticated expectation before freezing policy; a caller-supplied ref or self-asserted expectation alone is not trusted. The report SHALL bind the trusted-context digest plus expected and resolved target identities. A moved, mismatched, untrusted, missing, or unreadable target identity or policy SHALL yield UNKNOWN. The producer treats every context file as claimed provenance and emits only `range_candidate` after structural and identity checks; it has no producer-verifiable trust signal. Range without a valid context file emits `range_preview`. A protected consumer SHALL independently enumerate all best merge bases from workflow-native target/head identities, require exactly one, and derive the expected unique merge base plus complete governed merge-base-to-head diff. Under the protected policy it SHALL recompute the sorted governed Python selected-file/line manifests, governed policy path/section manifests, declared project-runtime source-lock path/blob/content manifests and `candidate_policy_change_digest`, diff digest, object-type/Git-mode/status/rename/deletion facts and digests; resolve the authorized target-tip policy/config identity; require the approved signed producer module/schema/profile/analyzer-toolchain identities; verify producer workflow/ref/run/attempt/job plus report-artifact identity/digest; and compare every value with the immutable producer report. On success it emits a separate verification envelope binding producer report digest, trusted event digest, repository/PR-or-queue/target/head identities, analyzed merge-base commit/tree, governed diff/selection/line/object-type/Git-mode/status/rename/deletion manifests and digests, selected policy/config source/package/version/commit/tree/blob/content/config digests and project-runtime descriptor/source-lock/build/artifact identities as applicable, approved producer module/schema/profile/toolchain identities, producer workflow/ref/run/attempt/job/artifact identities, verifier workflow/ref/run/attempt identity, consumer policy version, decision, and `effective_assurance_kind=pr_range`. Any missing governed input or merge-base, diff, selection, manifest, policy/config, producer, or artifact mismatch emits rejection/UNKNOWN. The consumer verifies selection and provenance; it does not independently re-run analyzers or claim to verify finding semantics. It SHALL NOT mutate the producer report, and no producer field or self-asserted context file alone satisfies a `pr_range` policy. The merge-base remains the source-code baseline, while the current authorized target-tip policy governs both source snapshots. The resolver SHALL manifest each selected analyzer input and declared analyzer-config input with the closed tagged `AnalyzerInputIdentity` union `git_blob | signed_module_payload | generated_projection | builtin_mode`. `git_blob` binds repository/commit/tree/path, tree-entry object type, exact Git mode, blob/content digests; `signed_module_payload` binds signed module name/version/checksum/signature/canonical path/content digest; `generated_projection` binds generator identity/schema, parent identity/digest, logical transform/root-substitution digest, and output digest; `builtin_mode` binds analyzer/tool version plus exact mode/argv and has no file. Only `git_blob` may populate a reviewed-repository blob field. Signed `tracked-regular-governed-input-v1` SHALL run before applicability and analysis. Every selected/eligible/invoked Python, test, test-support, policy, and configuration pathname must resolve in the index/commit tree to object type `blob` with mode `100644` or `100755`. A recognized governed pathname with symlink mode `120000`, gitlink mode `160000`, missing/unmerged/intent-to-add content, or any other type/mode remains governed impact and yields `unsafe_governed_input` UNKNOWN; it SHALL NOT be silently omitted, dereferenced, analyzed, or used to support NOT_APPLICABLE. `scope.py` SHALL traverse every materialized path component descriptor-relatively with no-follow/beneath semantics, reject symlink/non-directory parents, open the final component no-follow, require the same opened descriptor to be a regular file, and hash it against the committed blob and materialized-output digest. Every accepted materialized file also binds its output SHA-256, and producer plus protected consumer SHALL canonicalize and validate the same tagged representation; pass only materialized-root paths to analyzers; pass explicit target-policy config paths to configurable adapters; and verify every snapshot manifest before and after analysis. Ruff SHALL enumerate only repository-root `.ruff.toml`, `ruff.toml`, and `pyproject.toml:[tool.ruff]`, require exactly zero or one applicable source, use explicit `--isolated` for zero and explicit projected `--config` for one, and return `ruff_config_ambiguous` UNKNOWN before applicability/launch for multiple applicable sources, malformed/unsupported tables, or pinned-loader/catalog drift; an extended Ruff config SHALL come from a controller-resolved, preserved-layout, manifest-bound target-tip transitive `extend` closure whose relative in-tree nodes/edges/blob/content/graph digests are governed and whose absolute/escaping/symlink/missing/cyclic/unsupported or over-bound graph is UNKNOWN. Pylint explicit target-policy `--rcfile` or a sealed pinned-default config—with canonical non-empty `init-hook` and every non-empty `extension-pkg-allow-list`/`extension-pkg-whitelist` alias rejected before applicability/launch, and `load-plugins` limited to the signed profile's exact sealed plugin manifest, which is empty in initial `pr-range-v1`. Basedpyright an explicit per-snapshot projected `--project` rather than `.` or the policy-bundle config path—derived from one recognized target primary plus its sealed in-tree `extends`/`baselineFile` graph, or from exact generated `basedpyright-default-v1` whose canonical `include` array is the sorted eligible snapshot-relative file manifest when no primary exists. Semgrep an explicit `bundle_root` containing either the authorized target-tip clean-code policy or the contract-named sealed clean-code fallback from the exact signed installed Code Review module. For basedpyright, exactly one pinned-loader-recognized `pyrightconfig.json`, `[tool.pyright]`, or `[tool.basedpyright]` primary is allowed; conflict or loader/profile drift is UNKNOWN. The controller SHALL recursively resolve `extends` and optional `baselineFile` from the authorized target tree, manifest every ordered node/edge/path/blob/content/schema digest, govern every referenced path, and reject absolute/escaping/symlink/missing/cyclic/duplicate/unsupported or signed-bound-exceeding graphs. The pinned configuration and baseline schemas SHALL identify every filesystem/source-identity field (including nested execution environments and baseline entries); source-relative non-baseline values SHALL be rewritten to the corresponding merge-base or head materialization, and `venvPath`/`venv` SHALL resolve to the same canonical site-packages path inside the identical verified target-tip project-runtime layer for both sides, while the basedpyright executable remains in the analyzer capsule. The generated flattened project SHALL set `include` to the sorted exact eligible governed Python files using canonical snapshot-relative paths, clear every effective `exclude`, `ignore`, and path-scoped `strict`, reject non-empty target `executionEnvironments`, remove every effective `baselineFile` across the resolved graph, and be invoked only as explicit `--project <projection>` with no positional source paths or `--baselinefile`; original include/exclude/ignore/baseline identities remain governed evidence, while baseline artifacts are not analyzer-readable inputs. With no recognized primary, the controller SHALL generate exact `basedpyright-default-v1` with the sorted eligible snapshot-relative file manifest as its canonical `include` array and substitute only the active snapshot root. The original policy/reference/default digest, projection mapping/digest, resulting absolute roots, side config output digests, exact eligible/project-include manifests, and original/effective include/exclude/ignore/strict/execution-environment/baseline-control evidence SHALL be recorded. Unsupported path semantics, path escape, a path into the target-policy bundle/caller worktree, missing projected dependency, or injection mismatch SHALL yield UNKNOWN. Every index or range snapshot analyzer execution SHALL consume one manifest-bound `SnapshotInvocationContext` containing the snapshot commit/tree/root, exact working directory, allowed import roots, closed sorted `config_roots[]`, sealed analyzer-runtime-capsule/root/interpreter/bootstrap identity, optional verified project-runtime descriptor/layer identity and member allowlist, sanitized environment, process-private output/temp roots, sandbox backend/capability identity, and context digest. Every config-root entry SHALL bind analyzer consumer, typed input identity, logical role, source/projection/bundle digest, exact read-only mount point, and pre/post manifest digest. The list SHALL include every adapter-readable selected/default/projected input, including Ruff extend bundles, basedpyright project/non-baseline reference payloads, Semgrep selected/fallback bundles, Pylint config, and pytest/coverage side projections; an omitted, extra, writable, or identity-mismatched root is UNKNOWN. Each subprocess SHALL run with `cwd` equal to its materialized index or range source root. The environment SHALL remove caller/worktree/policy-bundle import paths and inherited `PYTHONPATH`, `PYTHONHOME`, editable-source roots, user-site and startup hooks. Every Python analyzer SHALL start with the capsule interpreter's `-I -S` flags through the sealed bootstrap while snapshot cwd/import roots are absent from startup `sys.path`; the bootstrap SHALL add sealed capsule analyzer paths without `site.addsitedir` or executable `.pth` processing, then install signed `capsule-reserved-imports-v1` before inserting validated snapshot roots after interpreter initialization. The signed catalog SHALL contain the exact top-level import prefixes, including descendants, for the capsule interpreter/stdlib/bootstrap, `specfact_code_review` built-ins, and every Python distribution in the analyzer-runtime lock. Before dispatch, the bootstrap SHALL reject as `reserved_import_collision` UNKNOWN any matching top-level `.py`, `.pyi`, regular-package, or namespace-package entry in the snapshot or project-runtime layer. A capsule-only finder SHALL remain ahead of those roots and verify every loaded reserved module origin is inside the sealed capsule. For non-reserved imports only, resolution order SHALL be active snapshot before project-runtime layer. Candidate `sitecustomize.py`, `usercustomize.py`, `site.py`, and `.pth` payloads SHALL NOT execute during startup. Targeted pytest SHALL disable automatic third-party plugin loading and enable only pinned declared plugins. Pylint dynamic hooks and repository/unapproved plugins SHALL be rejected before launch; only exact sealed profile plugins may execute. CrossHair imports, targeted pytest collection/execution, Pylint with sealed profile code, and every other import-capable analyzer SHALL resolve repository modules only from the active snapshot. Environment sanitization alone is insufficient. Every analyzer process SHALL run inside a fresh OS-enforced deny-by-default filesystem sandbox. The only initial accepted profile is `linux-bwrap-v1`, using only the signed static Linux x86_64 Bubblewrap ELF at canonical verified OCI-root path `/opt/specfact/bin/bwrap-static`. Its verified descriptor SHALL bind architecture, SHA-256, and empty `PT_INTERP`/`DT_NEEDED`; the controller SHALL open no-follow, hash and execute that same descriptor, clear loader-injection environment variables, and bind `pre-namespace-mapped-objects-v1` evidence proving no filesystem-backed mapped object or loader/library open beyond the executable before namespace creation. Dynamic linkage, descriptor/path substitution, unexpected pre-namespace mapping/open, another OS/backend, missing executable, or failed namespace/mount/network probe yields UNKNOWN. The sandbox uses the verified analyzer capsule as its complete read-only root filesystem and exposes only its active snapshot read-only, every and only declared `config_roots[]` mount read-only, the identical verified project-runtime layer only for the closed import-capable member set, and its own empty output/temp/cache/home roots writable. Host `/usr`, `/lib*`, interpreter, stdlib, extension-module, dynamic-loader/shared-library, and controller-runtime mounts are forbidden. The caller checkout, opposite snapshot, claimed/trusted context, target-policy or fallback source roots beyond the selected projected payload, controller/report state, sibling analyzer outputs, host credentials, any unverified or member-ineligible project dependency root, and network SHALL be absent or denied; undeclared file descriptors SHALL be closed. The trusted controller outside the sandbox SHALL capture argv plus OS-observed exit/stdout/stderr, accept artifacts only from that process-private output root after exit, validate declared shape/digests and all source/config manifests, classify them as `candidate_executed_observation`, and seal those exact bytes before dependent comparison. That seal proves post-collection immutability, not that candidate Python could not influence its own process or process-private artifact. The report SHALL bind sandbox backend/version, capability-probe result, mount/permission/network profile, and per-process root-manifest digest. Missing or failed isolation capability, denied-profile mismatch, cross-root access, unexpected output, or adapter unable to honor the context SHALL yield UNKNOWN; strict index/range assurance SHALL NOT fall back to an unsandboxed process. Adapter/config injection failure SHALL yield UNKNOWN. Index and range modes SHALL reject `--fix`, `--preview-fixes`, and `--with-mutation`. Any index conflict/object failure, materialization failure, path-root violation, or content-integrity failure SHALL yield UNKNOWN.

For this modules change, conformance implementation stops at producer `range_candidate`/`range_preview` behavior and the signed static schema/compatibility matrix. The protected workflow-native consumer and verification-envelope emitter are core-owned downstream adoption components. Module tests SHALL validate producer behavior and static accepted/rejected envelope fixtures only; core adoption tests SHALL independently prove event derivation, governed-scope recomputation, comparison, rejection, and envelope emission. Core-owned runtime selectors SHALL NOT enter this change's Requirements Evidence mapping or implementation checkpoint.

The report SHALL record requested/effective scope, assurance kind, repository root, index tree/blob identities when applicable, supplied base/head refs and resolved commit/tree SHAs, authenticated expected target-tip commit/tree plus trusted-context digest, sorted `merge_base_candidates[]` commit/tree identities and candidate-set digest, nullable analyzed merge-base commit/tree SHA, diff digest, selected files/lines and object-type/Git-mode/blob/content manifests, rename/deletion facts, filters/facets, trusted policy/config identity and per-snapshot config-projection digests, project-runtime descriptor/layer/source-lock/build/artifact identities when applicable, sandbox backend/capability and per-process root-manifest digests, `runtime_trust_model`, `adversarial_runtime_evidence`, per-member observation trust, resolver identity, status, and diagnostics.

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

#### Scenario: Governed Python and policy inputs must be tracked regular blobs

- **GIVEN** an index or range tree contains a recognized governed Python, test, test-support, policy, or configuration pathname
- **WHEN** scope selection and immutable materialization run
- **THEN** its manifest binds tree-entry object type, exact Git mode, blob SHA, content digest, and materialized-output digest
- **AND** only tracked blob modes `100644` and `100755` are accepted
- **AND** descriptor-relative no-follow traversal proves every parent is a directory and hashes the same opened regular final descriptor against the committed blob
- **AND** symlink `120000`, gitlink `160000`, missing/unmerged/intent-to-add, parent-symlink, mode/content mismatch, or any other unsafe type is `unsafe_governed_input` UNKNOWN before applicability/analyzers
- **AND** a regular-to-symlink `.py` change remains governed impact and can never be dereferenced, omitted, classified fixed, or converted to NOT_APPLICABLE.

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

- **GIVEN** range scope resolves successfully and the unfiltered merge-base-to-head diff contains neither governed Python/test/test-support input nor any `governed-policy-paths-v1` analyzer-policy/config change
- **WHEN** the report finalizes
- **THEN** status is NOT_APPLICABLE
- **AND** the report retains the full scope evidence, diff digest, and governed-selection policy
- **AND** rejected range-narrowing options cannot reach or manufacture this state
- **AND** it does not claim code quality passed.

#### Scenario: Candidate analyzer-policy change is governed and cannot self-authorize

- **GIVEN** an unfiltered range changes a closed governed analyzer-policy path or governed `pyproject.toml` tool section without changing Python
- **WHEN** range scope and assurance are derived
- **THEN** scope evidence binds the candidate policy path/section/status/rename/deletion manifest and `candidate_policy_change_digest`
- **AND** the range is applicable and records `candidate_policy_change_status=UNKNOWN`, not NOT_APPLICABLE or PASS
- **AND** both source snapshots continue to use the authorized target-tip policy
- **AND** candidate policy is shadow-only and cannot authorize its own current or future assurance
- **AND** `.coveragerc`/`.coveragerc.toml`, `resources/semgrep-rules/ai-bloat.yaml`, every target-tip Ruff transitive `extend` closure member, every pinned pytest source (`pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, plus the exact recognized sections in `pyproject.toml`, `tox.ini`, and `setup.cfg`), every closed Pylint source (`pylintrc`, `.pylintrc`, `pylintrc.toml`, `.pylintrc.toml`, and pinned-loader Pylint sections in `pyproject.toml`/`setup.cfg`/`tox.ini`), governed coverage sections, and the other analyzer-policy files are governed, while unrelated metadata in shared files is not
- **AND** strict merge authority requires a separate accepted policy-promotion/trust-epoch contract rather than a producer assertion.

### Requirement: Differential Base-Head Enforcement

Range enforcement SHALL analyze the resolved merge-base and head with identical shared analyzer/configuration identity: analyzer and toolchain identities; trusted target-policy/config source digest; projection algorithm/schema identity; and a canonical logical projection-map digest whose source-root placeholders are independent of either materialized path. Per-snapshot projected-config bytes and digests MAY differ because their absolute roots differ; those digests are materialization evidence and SHALL NOT be compared for raw equality. A mismatch in any shared identity field yields UNKNOWN, while a difference limited to the recorded side-specific root substitutions does not. The supplied base-ref tip SHALL NOT be used as the analyzer baseline when it differs from the merge base. Signed `finding-multiset-v1` SHALL classify findings without collapsing duplicate diagnostics. Its `identity_fingerprint` is SHA-256 over canonical JSON of analyzer ID, rule/kind ID, rename-normalized repository-relative path, exact analyzer-emitted qualified symbol or null, and a message normalized only by Unicode NFC, CRLF/CR-to-LF, validated active-snapshot-root replacement with `<SNAPSHOT>`, ASCII horizontal-whitespace collapse, and trim; digits, identifiers, quoted values, and arbitrary paths are not removed. Raw line/column/span and source context are excluded from identity and retained in `occurrence_evidence_digest`; identity equality alone SHALL NOT establish continuity. Schema 1.6 SHALL give every finding `location_kind=source_span|selector|non_source`. A source finding SHALL carry canonical `source-span-v1`: one-based inclusive start/end lines, zero-based UTF-8-byte start column and exclusive end column, `precision=exact|line`, plus raw analyzer coordinates/coordinate-system and conversion identity/digest. Each adapter SHALL preserve/convert exact endpoints when its pinned output supplies them. If it supplies only a valid one-based line, the controller SHALL use the entire LF-normalized physical line excluding its terminator (`start_column=0`, `end_column=UTF-8 byte length`, `precision=line`). Invalid/missing source path or line is invalid evidence and SHALL NOT be guessed. Selector findings use exact selector reconciliation outside source pairing; infrastructure/non-source findings remain typed UNKNOWN facts. Every required/conditional profile member SHALL emit one canonical location kind.

Signed `occurrence-continuity-v1` SHALL validate each canonical source span against the immutable source blob and compute `continuity_anchor_digest` from canonical JSON containing rename-normalized path, exact LF-normalized bytes of every physical line intersecting the span, the immediately preceding/following complete physical lines or BOF/EOF sentinels, and start/end columns relative to the first/last spanned lines. It SHALL perform no whitespace, comment, token, path, fuzzy, AST, symbol, move, or nearest-line normalization. An anchor is considered only when it identifies exactly one distinct physical source location in base and exactly one in head. Signed `source-line-correspondence-v1` SHALL compare the complete LF-normalized physical-line sequences with insertion/deletion cost 1, replacement cost 2, exact-line match cost 0, and no move operation. It SHALL record global minimum cost `G`, cost `F` with the exact contiguous anchor pairing forced, and cost `X` with that exact anchor pairing forbidden. `F=G` and `X>G` is proven; `F>G` is different; `F=G=X` or a non-unique anchor is ambiguous. Initial bounds are 16 MiB and 20,000 physical lines per side and 4,000,000 dynamic-programming cells per file pair; exceeding any bound is unavailable. Algorithm/version, bounds, line-sequence digests, anchor positions, `G/F/X`, and correspondence digest are evidence. Multiple identical analyzer emissions at one proven location retain counts. Within proven continuity, occurrences partition by normalized severity plus derived blocking-input digest; identical partitions pair deterministically by occurrence digest and are unchanged, while incompatible continuous residuals are unknown transitions. A different identity-equal head finding is introduced. Invalid spans, alternate-optimal/non-unique mappings, or unavailable bounds record `continuity_status=invalid|ambiguous|unavailable` and an unknown head transition; other unmatched head surplus is introduced, and unmatched base surplus is fixed subject to suppression and rename overrides. The only continuity states are `proven|different|ambiguous|invalid|unavailable`. The report binds canonical/raw spans, identity/anchor/partition counts, line-sequence/cost/correspondence evidence, continuity decisions, every pair/surplus occurrence, and bucket digest. An unrelated insertion before an exact anchor permits a line shift to remain unchanged only when forced correspondence is uniquely optimal; moving an identical block to another edit location is different or ambiguous, never silently unchanged; a second identical head emission at one proven location remains introduced; and location/context/duplicate/mixed-outcome uncertainty cannot collapse to PASS. A matching identity fingerprint is unchanged only when normalized severity and derived blocking inputs also match; any unclassified severity transition retains both observations and is unknown, never silently unchanged. Under conservative `rename-fix-policy-v1`, any base finding missing across a one-to-one rename is unknown and can never be fixed in CR14, regardless of file-byte changes; matching findings may remain unchanged and head-only findings may be introduced, but this change defines no semantic-subject inference. Before fingerprint comparison, the head file anchor for a resolved one-to-one rename SHALL be normalized to the recorded old/base path; copies and unpaired additions SHALL NOT be rename-normalized, and both original paths plus the rename fact SHALL remain in evidence. Before a missing base fingerprint can be classified fixed, the controller SHALL compare immutable base/head Python comment-token manifests under signed `suppression-directives-v1`. The registry SHALL cover the pinned profile's Ruff 0.15.12 parser-recognized source-suppression forms: inline/file-level noqa; case-sensitive `ruff:` `ignore[...]`, `file-ignore[...]`, `disable[...]`, and `enable[...]` directives under the pinned stable rule-code and preview rule-name selector grammar; and every isort action comment in both accepted prefix families (`isort:` and `ruff: isort:`) for `skip_file`, `on`, `off`, `skip`, and `split`; Pylint disable/disable-next/disable-all/legacy disable-msg/skip-file; basedpyright `type: ignore` plus every `pyright:` source directive recognized by pinned 1.39.10's parser—including line-level `pyright: ignore`, bracketed `pyright: ignore[reportRule,...]`, strict/basic/standard, the complete `getBooleanDiagnosticRules()` name/value catalog, and the complete diagnostic-level rule/value catalog; Semgrep nosemgrep/nosem; Coverage no-cover/no-branch pragmas; and every source directive recognized by pinned CrossHair 0.0.109: special on/off forms plus the complete `AnalysisOptionSet.directive_fields` catalog (`enabled`, `analysis_kind`, `specs_complete`, `max_iterations`, `per_condition_timeout`, `per_path_timeout`, `max_uninteresting_iterations`). The basedpyright and CrossHair registries SHALL block every recognized source directive without guessing whether its value strengthens analysis; `analyzeUnannotatedFunctions=false` is an exact basedpyright regression vector, and exact regressions SHALL include all pinned false aliases for `enabled` and non-positive `max_iterations`, `per_condition_timeout`, and `per_path_timeout` budgets. Each occurrence binds registry/tool identity, normalized family/analyzer/rules, rename-normalized path, exact line, token digest, and occurrence-manifest digest. A new, changed, or relocated head occurrence is always open and blocking in CR14: diagnostic-suppression families emit `introduced_inline_suppression`, while all recognized basedpyright source directives and CrossHair analyzer-result controls emit `introduced_analyzer_result_control`; candidate source/policy/justification or an unauthenticated injected object cannot waive it. CR14 has no suppression-waiver ingestion or verification contract; authenticated exceptions are deferred to `governance-02-exception-management`. Any missing head fingerprint for the same analyzer/path is unknown rather than fixed. Under signed `suppression-affected-edit-v1`, a content-changed governed Python file that retains any unchanged registered directive SHALL emit required `unchanged_suppression_on_changed_file` UNKNOWN evidence for every required or activated analyzer mapped to that occurrence before aggregate verdict derivation. The evidence SHALL bind analyzer ID, rename-normalized path, base/head blob digests, unchanged occurrence and manifest digests, and canonical changed-hunk digest. A byte-identical pure one-to-one rename is not a content change; removal of the last mapped occurrence does not trigger the quarantine, while a changed or relocated occurrence remains an introduced blocker. CR14 SHALL NOT infer directive reach, line scope, or an analyzer-specific unsuppressed mode. The canonical authority for `suppression-directives-v1` and `suppression-affected-edit-v1` SHALL be exactly the signed package resource `resources/contracts/pr-range-v1-suppression-catalog.json`, regenerated byte-for-byte from the implementation checkpoint. Its canonical bytes/SHA-256, schema/catalog/parser versions, recognized forms, analyzer mappings, normalization and disposition constants SHALL match the activated profile and SHALL be included in report and protected verification-envelope identity. Missing, embedded-only, extra, noncanonical, or checkpoint/package/profile/report resource drift is UNKNOWN before applicability or analyzer launch. The static consumer compatibility matrix SHALL contain matching and one-boundary-mismatched checkpoint/resource/package/profile/report/envelope identities; the paired protected core consumer SHALL independently load the approved catalog identity from the signed module/profile and reject any report/envelope mismatch as UNKNOWN rather than promote it to `pr_range`. Tokenization/registry/normalization/comparison uncertainty is UNKNOWN. Changed-line intersection SHALL be evidence only and SHALL NOT be the sole introduction rule.

#### Scenario: Ambiguous merge-base topology is unknown

- **GIVEN** resolved full base and head commits have zero or more than one best merge base, including a synthetic criss-cross history
- **WHEN** range scope enumerates all best merge bases
- **THEN** it records the candidate merge-base identities and diagnostic
- **AND** returns UNKNOWN before diff selection, materialization, analyzer execution, or assurance-kind promotion
- **AND** neither producer nor protected consumer chooses an arbitrary first result or synthesizes a virtual base.

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

#### Scenario: Introduced inline suppression cannot masquerade as a fix

- **GIVEN** the merge-base has an analyzer finding and the head adds, changes, or relocates a registered inline suppression in the same analyzer/path
- **WHEN** strict differential classification runs
- **THEN** comment-token manifests are compared before analyzer fingerprints under the signed `suppression-directives-v1` registry, including every Ruff noqa/ignore/file-ignore/disable/enable grammar vector and every isort/`ruff: isort:` action variant, Pylint `disable-all`, legacy `disable-msg=<rule-list>`, and atomic whole-file `skip-file` aliases with a mapped baseline-diagnostic-disappearance regression, the complete pinned basedpyright parser-derived source-directive catalog with `pyright: ignore`, `pyright: ignore[reportRule,...]`, and `analyzeUnannotatedFunctions=false`, and the complete pinned CrossHair source-directive catalog with explicit `enabled=no`, `per_condition_timeout=0`, `per_path_timeout=0`, and `max_iterations=0` regressions
- **AND** the new occurrence is an open blocking class-specific finding—`introduced_inline_suppression` for diagnostic suppressions or `introduced_analyzer_result_control` for every recognized basedpyright or CrossHair analyzer-result control—with normalized directive and immutable path/line/token evidence
- **AND** the missing base analyzer fingerprint is `unknown`, never `fixed`
- **AND** CR14 accepts no suppression-waiver input or injected trusted flag; authenticated exception support is deferred to `governance-02-exception-management`
- **AND** an unchanged occurrence, including an identical pure one-to-one rename, is retained but not introduced
- **AND** tokenization, registry, normalization, or manifest-comparison failure is UNKNOWN rather than PASS.

#### Scenario: Unchanged suppression in a changed file cannot hide a new defect

- **GIVEN** merge-base and head retain an identical registered suppression or analyzer-result-control occurrence in a governed Python file
- **AND** the file's committed blob content changes outside that directive
- **WHEN** strict differential classification runs
- **THEN** signed `suppression-affected-edit-v1` emits required `unchanged_suppression_on_changed_file` UNKNOWN evidence for every required or activated analyzer mapped to the occurrence
- **AND** the evidence binds analyzer ID, rename-normalized path, both blob digests, unchanged occurrence/manifest digests, and canonical changed-hunk digest
- **AND** the aggregate cannot PASS merely because both suppressed analyzer runs are silent
- **AND** CR14 performs no directive-reach or analyzer-native unsuppressed-mode inference
- **AND** a byte-identical pure one-to-one rename is not quarantined, removal of the last mapped occurrence follows ordinary analysis, and a changed or relocated occurrence remains an introduced blocker.

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
- **AND** the bundle also contains exactly one sealed AI-bloat pack: the authorized target-tip `resources/semgrep-rules/ai-bloat.yaml` when present, otherwise the canonical payload from the same exact signed module; the report binds its source/blob/content/materialized digests and both sides use it identically
- **AND** a candidate AI-bloat-pack edit is governed UNKNOWN and cannot self-authorize, while missing/untrusted/digest-mismatched fallback evidence is UNKNOWN
- **AND** this clean-code/AI-bloat fallback does not make `semgrep-bugs` applicable when the authorized target-tip bugs configuration is absent.

#### Scenario: basedpyright projects relative paths into each source snapshot

- **GIVEN** the trusted target policy contains relative basedpyright source/import paths
- **WHEN** merge-base and head analysis is prepared
- **THEN** the pinned configuration schema rewrites every source-relative path to the corresponding immutable source root
- **AND** `venvPath`/`venv` resolve to the same canonical site-packages path inside the identical verified target-tip project-runtime layer on both sides, while the analyzer executable remains in the sealed capsule
- **AND** basedpyright receives a distinct manifest-bound projected `--project` artifact for each side, never the policy-bundle config path or process `.`
- **AND** an imported dependency is read from the appropriate merge-base or head snapshot
- **AND** unsupported, escaping, external, or missing projected paths yield UNKNOWN.

#### Scenario: basedpyright baseline policy is governed but cannot suppress authoritative diagnostics

- **GIVEN** the authorized target primary recursively uses `extends` and optionally names `baselineFile`
- **WHEN** policy impact and per-snapshot projects are resolved
- **THEN** every target-tip reference node/edge and baseline path/blob/content/schema digest is manifested and every referenced path is governed
- **AND** a candidate-only change to an extended config or baseline artifact is governed UNKNOWN rather than NOT_APPLICABLE
- **AND** both sides receive projections from the same sealed logical graph with every effective `baselineFile` removed and no `--baselinefile` argument
- **AND** the baseline artifact is not placed in `config_roots[]`, mounted, or read by authoritative basedpyright analysis
- **AND** a relocated/new diagnostic equivalent to a previously baselined diagnostic remains observable
- **AND** a non-empty effective baseline reference, CLI injection, or absolute/escaping/symlink/missing/cyclic/duplicate/unsupported/over-bound reference input yields UNKNOWN.

#### Scenario: basedpyright has a sealed no-config input

- **GIVEN** the authorized target contains no recognized pyrightconfig.json, tool.pyright, or tool.basedpyright primary
- **WHEN** mandatory basedpyright analysis is planned
- **THEN** the controller generates a distinct side project from `basedpyright-default-v1` whose canonical `include` array is the sorted exact eligible snapshot-relative file manifest
- **AND** the generator/profile/schema plus pinned basedpyright 1.39.10 toolchain digest and side substitution/output digest are evidence
- **AND** each invocation uses explicit `--project <side-project>` and never process `.` or implicit source/config discovery
- **AND** generation, substitution, integrity, or injection mismatch yields UNKNOWN.

#### Scenario: Import-capable analyzers stay inside each materialized snapshot

- **GIVEN** an imported repository dependency has different content at merge base and head while caller/worktree source is also present
- **WHEN** Ruff, Radon, Pylint, basedpyright, either Semgrep pass, CrossHair, targeted pytest, or any other analyzer subprocess executes for each side
- **THEN** each process uses that side's materialized source root as OS `cwd`, but Python starts with the capsule interpreter's `-I -S` flags through the sealed bootstrap so cwd is absent from startup `sys.path`
- **AND** its sanitized import environment initially contains only sealed capsule analyzer roots; validated snapshot roots are inserted by the bootstrap as data only after interpreter startup and without `site.addsitedir` or executable `.pth` processing
- **AND** pytest automatic plugin loading, startup `PYTHONPATH`, site/user-site processing, caller/user hooks, and candidate `sitecustomize.py`/`usercustomize.py` execution are disabled
- **AND** every subprocess uses the sealed executable/cwd/environment/output context, and merge-base import-capable execution imports merge-base content while head execution imports head content
- **AND** caller/worktree/policy-bundle source resolution or invocation-context mismatch yields UNKNOWN.

#### Scenario: Candidate startup hooks cannot run before a Python analyzer

- **GIVEN** the active snapshot root contains side-effecting `sitecustomize.py`, `usercustomize.py`, `site.py`, and executable `.pth` payloads
- **WHEN** an import-capable Python analyzer starts from that snapshot cwd
- **THEN** the capsule interpreter starts with `-I -S` through the sealed bootstrap while snapshot roots are absent from startup `sys.path`
- **AND** the bootstrap adds only verified capsule analyzer roots, does not execute site or `.pth` processing, installs the signed reserved-prefix guard, and inserts validated snapshot roots only after interpreter initialization
- **AND** none of the candidate startup payloads executes before analyzer dispatch
- **AND** missing isolation flags, early snapshot-path exposure, bootstrap drift, or observed startup side effect yields UNKNOWN.

#### Scenario: Snapshot cannot shadow capsule-reserved imports

- **GIVEN** an immutable snapshot or project-runtime layer defines a top-level module, stub, regular package, or namespace-package component matching `pytest`, `pylint`, `radon`, `crosshair`, `specfact_code_review`, or any other exact prefix in `capsule-reserved-imports-v1`
- **WHEN** the sealed bootstrap prepares an import-capable analyzer
- **THEN** it preflights both mutable roots and records `reserved_import_collision` UNKNOWN before analyzer dispatch
- **AND** the capsule-only finder remains ahead of snapshot and project roots for every reserved prefix and descendant, and every observed reserved-module origin must be inside the sealed capsule
- **AND** candidate or project-layer bytes under a reserved prefix are never executed as analyzer/runtime code
- **AND** for a non-reserved module present in both roots, the active snapshot copy resolves before the project-runtime copy
- **AND** the report binds the exact prefix-catalog digest, import-search order, collision manifest, and observed-origin audit.

#### Scenario: Bubblewrap launcher is sealed before namespace creation

- **GIVEN** strict range analysis selects `linux-bwrap-v1`
- **WHEN** the controller verifies and launches Bubblewrap before its namespace exists
- **THEN** the signed payload is a Linux x86_64 static ELF with expected architecture, exact descriptor-byte SHA-256, and no `PT_INTERP` or `DT_NEEDED`
- **AND** the controller executes the already-verified no-follow descriptor with loader-injection variables removed rather than resolving the path again
- **AND** `pre-namespace-mapped-objects-v1` observes only that executable plus kernel pseudo-mappings and no other filesystem-backed mapping or loader/library open
- **AND** a dynamic executable, host loader/library dependency, descriptor/path substitution, or unexpected mapped object is UNKNOWN before any analyzer runs.

#### Scenario: Analyzer capsule boots without host runtime mounts

- **GIVEN** a verified `analyzer-runtime-capsule-v1` for a supported Linux x86_64 CPython environment
- **WHEN** Bubblewrap launches its sealed interpreter and a synthetic analyzer in an otherwise empty namespace
- **THEN** the capsule root manifest supplies every interpreter, stdlib, extension-module, dynamic-loader/shared-library, analyzer, native-tool, and bootstrap file needed to start
- **AND** no host `/usr`, `/lib*`, interpreter, runtime library, or controller path is mounted or resolved
- **AND** missing/extra capsule paths, host-runtime access, loader failure, or root-manifest drift yields UNKNOWN without fallback.

#### Scenario: Snapshot context mounts every sealed analyzer configuration input

- **GIVEN** planned adapters require a Ruff extend bundle, basedpyright project and non-baseline reference payload, Semgrep selected/fallback bundle, Pylint config, and pytest/coverage projections
- **WHEN** a snapshot invocation context and sandbox are built
- **THEN** each required input appears exactly once in sorted `config_roots[]` with consumer, typed identity, role, digest, read-only mount, and pre/post manifest
- **AND** the sandbox exposes every declared root and no unlisted policy/config root
- **AND** an omitted baseline/bundle/projection, extra or writable mount, or identity mismatch is UNKNOWN before analyzer launch.

#### Scenario: Analyzer sandbox denies cross-root evidence access

- **GIVEN** distinct caller, merge-base, head, context, policy-source, controller, and sibling-output roots contain unique sentinel files
- **WHEN** a synthetic import-capable analyzer, targeted pytest case, or CrossHair target attempts absolute, relative, symlink, descriptor, or network access outside its declared active snapshot and process-private output/temp roots
- **THEN** the OS sandbox denies every cross-root read and write and exposes no host credentials or network
- **AND** the verified analyzer capsule is Bubblewrap's complete read-only root filesystem, with no host interpreter, stdlib, extension-module, dynamic-loader/shared-library, `/usr`, or `/lib*` mount; the active snapshot and exact selected config inputs are separately read-only while only that process's empty output/temp/cache/home roots are writable
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

Strict PR-range assurance SHALL use the closed schema-versioned `pr-range-v1` profile defined authoritatively in `run/runner.py` and bound in the report by profile ID and policy/config digest. Its signed released module SHALL carry an analyzer-environment lock that provisions every member/loader through an exact `==` entry matching the frozen implementation checkpoint; the lock SHALL include direct `pytest==9.0.3` and `coverage==7.15.4` entries plus exact checkpointed pytest-cov, basedpyright 1.39.10, Pylint 4.0.7, Ruff, Semgrep, Radon, and CrossHair entries. Analyzer-only direct/transitive distributions SHALL NOT appear in `module-package.yaml:pip_dependencies`; that marketplace field remains limited to host/controller imports and SHALL NOT receive the isolated analyzer closure. Python components bind signed wheel SHA-256 or canonical RECORD payload-manifest digest plus normalized entry point and sealed interpreter, never environment-specific console-script bytes; native executables retain exact platform/version/executable hashes. The signed `toolchain-lock-schema-1` resource SHALL bind `oci-distribution-acquisition-v1`: exact HTTPS registry/repository@manifest digest; config digest; ordered layer digests/diff IDs/media types/sizes; signed redirect-host allowlist; OCI distribution/rootfs/whiteout schemas; cache key/schema and acquisition bounds; a frozen checkpoint canonical-lock projection plus SHA-256 that the later generated signed resource must match exactly; plus a fixed `/opt/specfact/wheelhouse` filename/platform/size/SHA-256 manifest containing every selected direct/transitive lock member. Tags, mutable URLs, caller-supplied sources, or a digest without its signed locator are invalid. A controller-owned outside-checkout content-addressed cache SHALL rehash every read; a complete verified cache supports offline use, while a miss may fetch only through the signed locator before sandbox launch. Every redirect hop/final target SHALL remain HTTPS and match the signed host/path allowlist before credentials are attached; credentials are stripped and re-authorized per hop, and the ordered redirect chain/statuses/final URL/credential-sent facts plus digest are evidence. Credentials remain controller-only. Fetch/auth/redirect/downgrade/unauthorized-credential/media/size/timeout/digest failure, partial cache, or cache miss with unavailable network is UNKNOWN without host/runtime fallback. Safe extraction SHALL apply pinned whiteout semantics and reject path traversal, device nodes, unsafe links, collisions, or final-root mismatch. The resource SHALL also enumerate the complete evaluated analyzer dependency DAG and exact constraints/payloads for each supported Linux x86_64 CPython 3.11–3.13 environment, with canonical capsule mount/interpreter/bootstrap paths and a separate minimal bootstrap allowlist. `toolchain.py` SHALL materialize `analyzer-runtime-capsule-v1` from that rootfs plus a canonical exact/hash-checked analyzer install input without feeding entries to the host resolver. The final sealed root manifest SHALL include the interpreter, stdlib, extension modules, dynamic loader/shared libraries, analyzer distributions, signed built-in module-code payload, native tools, and bootstrap; the analyzer installed set SHALL equal exactly the environment lock plus bootstrap entries. Controller/core/module host distributions and runtime files are outside the capsule, excluded from analyzer paths/mounts, and never treated as analyzer inputs. The only Code Review Python code permitted inside is `module-code-payload-v1`. Under signed `verified-installed-module-payload-v1`, `toolchain.py` consumes the already-enabled module root from loader registration, requires official/approved origin plus the installed module name/version/checksum/signature package identity, re-runs the deterministic full-module-payload checksum and verifies its signature with the protected approved-key fingerprint, then copies the complete canonical `specfact_code_review` payload through descriptor-relative no-follow regular-file reads into `/opt/specfact/builtin/specfact_code_review`. It binds module/version/checksum/signature/key/loader/origin/root, verification algorithm/result, every canonical payload path/type/mode/size/content digest, allowed built-in entry modules/modes, payload-manifest digest, sealed destination and final-root digest. The original marketplace archive or archive cache is not required or reacquired, and the installed root is never mounted/imported by analyzers. `ai-bloat-ast` and `ast-clean-code` SHALL launch from that payload under the sealed interpreter/bootstrap. A `builtin_mode`, runner-file hash, unverified controller path, inferred partial import closure, missing/extra canonical payload member, failed loader/origin/checksum/signature/key/descriptor verification, or payload/root drift is UNKNOWN before analysis; every OCI layer, rootfs path, edge, marker, version, payload and closure digest must match, including transitive pluggy, nodejs-wheel-binaries, z3-solver, and all other resolved dependencies. Bare/lower-bound lock entries, an analyzer-only package declared as a host `pip_dependency`, missing/changed OCI layer or interpreter/stdlib/extension/loader/library/bootstrap path, any required host-runtime mount, missing direct loader entries, capsule payload/entry-point drift, or runtime version/root-manifest mismatch make profile activation UNKNOWN. Project/test dependencies required by repository code SHALL come only from a separate authenticated `project-runtime-layer-v1`, never from the analyzer lock or controller host. Its descriptor SHALL bind the authorized target repository/commit/tree, explicit target dependency-input path/blob/content identities, Python ABI/platform, complete exact distribution/native DAG and payload/entry-point/closure identities, immutable OCI locator/config/layers/root manifest, and builder workflow/ref/run/artifact/attestation. The identical read-only layer SHALL be used for merge-base and head and exposed only to the closed import-capable set `basedpyright`, `pylint`, `contracts`, and `targeted-pytest-coverage`; reviewed-project code comes only from the active snapshot for non-reserved imports. Signed `capsule-reserved-imports-v1` SHALL keep the exact capsule import prefixes ahead of both mutable roots and reject any snapshot/project-layer collision before dispatch. The layer SHALL exclude the reviewed project distribution and every reserved analyzer/runner/bootstrap component. Missing/untrusted/mismatched/candidate-controlled/per-side-different evidence, reserved collision, host fallback, or import failure is UNKNOWN. The producer remains `range_candidate`; only a protected consumer that independently verifies target-tip inputs, build provenance, artifact digest, and report binding may emit `pr_range`. Required analyzer IDs are `ruff`, `radon`, `semgrep`, `ai-bloat-ast`, `ast-clean-code`, `basedpyright`, `pylint`, and `contracts`. The mandatory `semgrep` member SHALL use the authorized target-tip clean-code policy when present and otherwise the sealed clean-code fallback from the exact signed installed Code Review module; absence or integrity failure of both is UNKNOWN, not optional or NOT_APPLICABLE. `semgrep-bugs` is conditionally required when the trusted target-base-tip policy snapshot contains the governed bugs configuration; `targeted-pytest-coverage` is conditionally required when the complete range contains governed runtime-measurable production `.py` or any governed Python test/test-support input. When the semgrep-bugs condition is absent its outcome SHALL be NOT_APPLICABLE rather than skipped. Targeted pytest is NOT_APPLICABLE only when the complete range contains neither governed runtime-measurable production `.py` nor governed Python test/test-support input; a `.pyi`-only range therefore leaves this member NOT_APPLICABLE while static analyzers remain required. The profile has no optional analyzers, and range cannot disable the targeted pytest member with `--no-tests`. This strict completeness is evaluated under `runtime_trust_model=candidate-not-intentionally-subverting-observer-v1`; the report and protected envelope SHALL carry `adversarial_runtime_evidence=false`. If consumer policy requires hostile-candidate-resistant runtime evidence, candidate-executing members and aggregate assurance are UNKNOWN rather than PASS.

The report SHALL list each profile member with required/conditional status; `execution_state=ran|error|not_applicable`; `evidence_outcome=PASS|FAIL|UNKNOWN|NOT_APPLICABLE`; per-snapshot version, toolchain and typed configuration/input identities/digests; duration; and diagnostics. `FAIL` is reserved for valid completed evidence that violates policy, including blocking analyzer findings and collected targeted-test assertion/skip/xfail/xpass outcomes. `UNKNOWN` is required for unavailable tools, launch errors, timeouts, unexpected process exits, parse errors, identity/config mismatch, missing artifacts, selector/count/JUnit/coverage reconciliation errors, or otherwise incomplete required execution. The generic term `failed` SHALL NOT collapse these states. After successfully resolved applicability plus differential/lifecycle classification, aggregate precedence SHALL be: NOT_APPLICABLE only for complete no-governed-impact evidence; otherwise FAIL if any valid completed blocker remains open after classification; otherwise UNKNOWN if any required member is unknown; otherwise PASS. A baseline-only analyzer/test/threshold FAIL paired to valid head PASS under identical policy remains retained per-snapshot fixed evidence and SHALL NOT enter the aggregate blocker set. A mixed blocking finding plus infrastructure/reconciliation UNKNOWN therefore has aggregate FAIL, non-shadow exit 1, and `has_unknown_required_evidence=true`; every unknown member and diagnostic remains authoritative evidence and the summary SHALL NOT claim complete coverage. Legacy verdict and exit fields derive only from aggregate authoritative `assurance_status`, so an UNKNOWN with no known blocker projects to non-shadow exit 1/legacy FAIL without becoming semantic FAIL. For every profile member, the planner SHALL derive eligible inputs independently for the merge-base and head from their immutable manifests. Signed `governed-input-completeness-v1` SHALL bind sorted eligible and exact invoked input manifests plus the pinned analyzer option-catalog/effective-control digest. Its initial transforms always pass Ruff 0.15.12 `--no-cache` and `--no-force-exclude`, canonically clear Ruff `per-file-ignores`, `extend-per-file-ignores`, `per-file-target-version`, and `namespace-packages`, set `src` to the active immutable snapshot root, and retain one shared global `target-version`, canonically clear Pylint 4.0.7 `ignore`, `ignore-patterns`, `ignore-paths`, `ignored-modules`, `ignored-classes`, `generated-members`, `ignore-none`, `ignore-on-opaque-inference`, `ignore-mixin-members`, `ignored-checks-for-mixins`, `mixin-class-rgx`, `signature-mutators`, and target-added `contextmanager-decorators` under signed `pylint-result-controls-v1`, and set basedpyright 1.39.10 `include` to the sorted exact eligible snapshot-relative file manifest, clear `exclude`, `ignore`, and path-scoped `strict`, reject non-empty target `executionEnvironments`, and remove every effective `baselineFile` while forbidding positional source arguments and `--baselinefile`. A cache write, effective whole-file exclusion, eligible/invoked mismatch, ineffective projection/flag, or option-catalog/help/schema drift is incomplete required execution and therefore UNKNOWN. These transforms do not change analyzer rule semantics; they prevent a governed input from being silently omitted or wholly silenced. A side with zero eligible inputs MAY record NOT_APPLICABLE only with its snapshot commit/tree, input-class identity, empty eligible-input set, manifest digest, and `absence_reason=no_eligible_inputs_in_snapshot`; this is explicit coverage truth, not a skipped/missing analyzer. If any eligible input exists on that side, NOT_APPLICABLE is forbidden and unavailable, skipped-without-valid-semantic-test-evidence, launch/process-error, timed-out, unparsable, artifact/reconciliation-defective, or identity-mismatched required analysis SHALL record that member as UNKNOWN; aggregate status follows the closed precedence rule. A per-snapshot NOT_APPLICABLE result does not make the whole range NOT_APPLICABLE when the opposite side or the range contains governed Python. This rule covers add-only and delete-only ranges without allowing an adapter's unrecorded empty-file early return to count as success. Zero findings SHALL count as successful coverage only when an explicit successful run record exists; an empty finding list alone is not analyzer evidence. Targeted pytest coverage SHALL use signed `complete-pytest-suite-v1`, not a source-to-test mapping. A range change to governed runtime-measurable production `.py`, Python tests, or Python test-support activates the member. Signed `runtime-measurable-production-v1` classifies tracked regular governed production `.py` as runtime-measurable and governed `.pyi` stubs as static-analysis-only; a `.pyi`-only range is NOT_APPLICABLE for targeted pytest/coverage while every applicable static analyzer still includes the stub. The controller SHALL collect the complete pytest selector inventory independently at merge base and head using the identical sealed target-tip policy projected onto each snapshot, starting from the policy's complete explicit `testpaths` roots or repository-root default and passing no production-derived positional file or selector narrowing. It SHALL bind collection roots, every exactly collected canonical node ID and source path, sorted eligible governed test/test-support input manifest, selector/inventory digest, pytest/coverage versions, analyzer-capsule/project-runtime/config identity, and collection artifact digest. Before collection, signed `pytest-input-role-v1` SHALL classify every governed test-side `.py` from only its immutable path and the identical authorized target-tip pytest 9.0.3 effective `testpaths`/repository-root default plus exact pinned `_pytest.pathlib.fnmatch_ex` matcher. The classifier SHALL pass the same materialized absolute `Path` form used by pytest's `path_matches_patterns`; on the initial Linux profile a pattern without `/` matches `path.name`, a pattern with `/` matches `str(path)`, a relative path-bearing pattern is prefixed with `*/`, and final matching uses Python `fnmatch.fnmatch`, retaining the pinned whole-string `**` behavior. Pytest source/policy/matcher digest and vectors SHALL be bound. `conftest.py` is `test_support`; a regular `.py` below a collection root whose path matches `python_files` under that algorithm is `test_candidate`; another regular `.py` below that root is `test_support`; and a separately governed test-facet path outside collection roots is `test_candidate_outside_root`, never support. Contents, AST, `__test__`, marks, decorators, selector counts, and collection outcomes SHALL NOT affect the role. Per-side role manifests and the shared policy/classifier digest are evidence. Every path classified as a candidate in either snapshot SHALL contribute at least one selector on every extant candidate side, whether or not it changed. Missing collection is `uncollected_test_candidate` UNKNOWN; becoming empty, setting `__test__ = False`, moving outside a collection root, or renaming to a support-shaped path retains the more specific `uncollected_changed_test` reason rather than reclassification. Only a path frozen as support before collection may omit selectors. The role/collection manifest reconciliation SHALL therefore catch whole-file omission by `norecursedirs` or collection hooks even on a production-only range. Each side SHALL execute its complete collected inventory and bind JUnit digest, per-selector collected/passed/failed/skipped/xfailed/xpassed/deselected outcomes, aggregate counts, per-snapshot outcome, and coverage artifact digest. After recorded one-to-one pure-file-rename normalization, every baseline selector absent at head is `removed_selector` UNKNOWN and every head-only selector must execute and pass. Delete-only production and changed/deleted test-support still require the complete head suite; there is no per-source plan to omit. A side MAY record NOT_APPLICABLE only when immutable evidence proves the entire side has no governed runtime-measurable production `.py`, Python test, or test-support input, with the empty manifests and `absence_reason=no_eligible_inputs_in_snapshot`; new selectors do not excuse an otherwise populated baseline side. Only an exact head inventory in which every selector collects exactly once and passes may satisfy the member. Head skip/xfail/xpass is FAIL; missing/duplicate/deselected selector, no-tests-collected, collection/JUnit/count mismatch, or uncollected changed test is UNKNOWN. A valid baseline non-passing selector that passes under the same normalized identity at head is fixed/non-blocking; uncertainty remains UNKNOWN. CR14 SHALL NOT infer related tests from production names, paths, imports, coverage, or arbitrary Python, SHALL NOT accept a candidate-authored impact map, and SHALL NOT claim that the pytest-recognized suite is complete stakeholder intent. Pytest/coverage SHALL disable candidate config discovery and sanitize `PYTEST_ADDOPTS`, `COVERAGE_RCFILE`, and coverage overrides. Before collection, signed `pytest-selection-controls-disabled-v1` SHALL parse and canonicalize both the complete effective target `addopts` token stream and the complete effective configuration field/value map with the exact pinned pytest 9.0.3 plus pytest-cov parser/help/`addini` catalogs, including short/long aliases and `--option=value` forms. Positional selectors and every option classified as `collection_selector`, `cache_selector`, `execution_short_circuit`, `discovery_override`, `plugin_override`, or `coverage_override` SHALL yield `pytest_selection_policy_unsupported` UNKNOWN. The initial closed regressions SHALL cover `-k`, `-m`, `--ignore`, `--ignore-glob`, `--deselect`, `--lf`/`--last-failed` and related cache selectors, `-x`/`--exitfirst`, `--maxfail`, stepwise controls, collect-only, `--pyargs`, `--confcutdir`, `--noconftest`, target `-c`/`--rootdir`, `-p`, `--override-ini`, and target-supplied pytest-cov source/disable/config/threshold/report controls. Only catalogued non-selecting options/fields MAY survive. Controller-owned roots, side config, complete collection, JUnit, coverage source/config/threshold, and private output argv SHALL be appended afterward. Sealed `testpaths`, `python_files`, `python_classes`, and `python_functions` remain declarative suite identity. Every other effective ini/TOML field SHALL be classified as `non_selecting`, `read_source`, `write_output`, `selection_filter`, `discovery_override`, `plugin_override`, or `coverage_override`; a non-empty/nondefault unsupported class is UNKNOWN, and non-empty `norecursedirs` SHALL always be `pytest_selection_policy_unsupported`. Original/canonical/rejected/effective argv/config maps, option/field classifications, parser/help/`addini`/catalog/plugin digests, and controller argv digest SHALL be evidence. Unknown tokens/fields, alias ambiguity, plugin-added options/fields, ineffective removal, or catalog drift is UNKNOWN. Pytest selection SHALL reproduce the signed source order of the exact pinned pytest 9.0.3 locator. A present `pytest.toml` or `.pytest.toml` SHALL match before every lower source even when zero bytes and MAY contain no `[pytest]` table. A present `pytest.ini` or `.pytest.ini` SHALL likewise match ahead of lower sources even when empty. Next, `pyproject.toml` primarily matches exactly one of native `[tool.pytest]` or legacy `[tool.pytest.ini_options]`, `tox.ini` matches `[pytest]`, and `setup.cfg` matches `[tool:pytest]`; when none of those sources matches, a present bare `pyproject.toml` SHALL be the final pinned fallback configfile. Options SHALL never merge. The controller SHALL manifest every present candidate, select the first match under that exact algorithm, and record selected section-or-empty/fallback reason plus every ignored lower-precedence source. Dual pyproject tables, parse/shape error, pinned loader/profile drift, or non-reproducible selection is UNKNOWN. Absence uses generated pinned `pytest-default-v1`. The controller SHALL derive separate merge-base and head pytest projections from that one logical target policy. Using the pinned pytest 9.0.3 path schema, it SHALL classify every path-bearing config field and trusted-addopts/argv token as read/source or writable output. It rewrites read paths including `pythonpath` and `testpaths` onto the matching immutable snapshot. It rewrites `cache_dir`, `log_file`, `--basetemp`, `--junitxml`/`--junit-xml`, `--log-file`, and every other pinned writable destination into deterministic role-specific paths below that process's private cache/temp/output roots; the controller-owned JUnit path wins and collisions are rejected. It invokes each side with explicit `-c <side-projection>` plus `--rootdir <side-snapshot-root>`. Absolute/escaping/unsupported/missing read paths, unclassified output tokens, outside-root writes, collisions, unexpected outputs, or ineffective transformation are UNKNOWN. Evidence SHALL bind the original source/section digest, loader/version/source-order/schema, canonical logical transform map, side root substitutions, side output digests, effective argv/options, and pre/post integrity. Coverage SHALL independently consume only an explicit controller-supplied target-tip `--cov-config` projection outside both snapshots, or generated pinned `coverage-default-v1`. The pinned Coverage 7.15.4 schema SHALL classify every path field as read/source input or writable data/report output. The controller SHALL rewrite every writable field—including `data_file`, debug output, and HTML/XML/JSON/LCOV/annotation destinations—plus pytest-cov report paths into deterministic role-specific locations below that analyzer's empty process-private output root. It SHALL bind original value, field role, output-root substitution, effective path/glob, projection/map/output digests, argv, and pre/post integrity; no snapshot, config, caller, or shared evidence root may be an effective write target. Unclassified output fields, escape/collision, unexpected output, or mismatch is UNKNOWN. It SHALL reproduce the signed pinned Coverage 7.15.4 order `.coveragerc`, `.coveragerc.toml`, `setup.cfg`, `tox.ini`, `pyproject.toml`, manifest every present recognized source/section, select the first applicable source, and retain ignored lower-precedence identities. Loader/profile drift, parse/shape failure, or non-reproducible selection is ambiguity UNKNOWN. Signed `coverage-exclusions-disabled-v1` SHALL require target `[report] exclude_lines`, `exclude_also`, `partial_branches`, and `partial_also` to be absent or canonically empty, then explicitly clear Coverage 7.15.4 built-in exclusion/partial-branch defaults plus additive lists in the generated projection. Any non-empty/unclassified alias, schema drift, or ineffective clearing is `coverage_exclusion_policy_unsupported` UNKNOWN before launch. Original/effective normalized lists and transform/projection digests are evidence. The controller SHALL canonicalize Coverage `[run] plugins`; only entries in the signed profile's sealed plugin manifest may load, and that manifest is empty in initial `pr-range-v1`. Any repository, unresolved, duplicate, wildcard, or unapproved Coverage plugin is UNKNOWN before launch, no repository plugin code is imported, and CR14 performs no plugin import-closure inference. Candidate coverage/test config remains shadow-only and is governed policy impact. Pytest unavailability, timeout, collection/internal/usage error, unexpected no-tests-collected, missing/duplicate/deselected selected tests, JUnit/count mismatch, missing/unreadable coverage, config ambiguity, projection failure, or effective-option mismatch SHALL be `execution_state=error`, `evidence_outcome=UNKNOWN`; collected head assertion failures and selected head skip/xfail/xpass outcomes SHALL be `execution_state=ran`, `evidence_outcome=FAIL`. A complete readable/reconciled coverage run below the sealed threshold SHALL be `execution_state=ran`, `evidence_outcome=FAIL` and bind configured threshold, measured total/per-file values, config/artifact digests, and semantic exit. A baseline threshold FAIL repaired under the identical policy at head is fixed/non-blocking; head threshold FAIL remains blocking. An exact all-selected-passed run satisfying the threshold records ran/pass and its coverage findings. Analyzer adapters SHALL surface timeout, unavailable, parse, and documented tool/process-exit failures explicitly. The required `contracts` member includes the CrossHair subprocess; a CrossHair timeout or documented process-error exit (including exit code 2 with no parsed counterexample) SHALL record `execution_state=error`, `evidence_outcome=UNKNOWN` with exit/stderr diagnostics rather than FAIL or empty success. A successfully parsed CrossHair counterexample remains a contracts finding and SHALL NOT be relabelled as infrastructure uncertainty.

#### Scenario: Signed module provisions the exact profile toolchain outside the host resolver

- **GIVEN** a signed Code Review module release claims `pr-range-v1`
- **WHEN** its analyzer-environment lock, host dependency manifest, and a fresh dedicated analyzer installation are verified
- **THEN** every distribution-backed profile member and configuration loader has an exact checkpoint-matching `==` lock entry, while each built-in member has a valid signed `module-code-payload-v1` identity
- **AND** pytest 9.0.3, Coverage 7.15.4, basedpyright 1.39.10, Pylint 4.0.7, exact checkpointed pytest-cov, and every other analyzer dependency are direct or explicitly checkpointed in that lock as required
- **AND** Coverage is a direct lock member rather than an unbound pytest-cov transitive dependency
- **AND** no analyzer-only direct or transitive lock member appears in host `module-package.yaml:pip_dependencies`
- **AND** installation beside a supported host with differing compatible dependencies reaches `toolchain.py`, which provisions the lock into its separate analyzer root
- **AND** a bare/lower-bound lock entry, analyzer entry leaked into host dependencies, missing direct loader, lock resolution drift, or installed version/digest mismatch yields UNKNOWN before analysis.

#### Scenario: Built-in analyzers boot from the signed module payload inside the capsule

- **GIVEN** `ai-bloat-ast` and `ast-clean-code` are mandatory `pr-range-v1` members
- **WHEN** the analyzer capsule is built and each member is launched
- **THEN** `toolchain.py` re-verifies the loader-registered signed Code Review installation under `verified-installed-module-payload-v1` and materializes its complete canonical `specfact_code_review` package payload at `/opt/specfact/builtin/specfact_code_review`
- **AND** `module-code-payload-v1` binds package/version/checksum/signature, protected key fingerprint, loader/origin/root identities and the real installed module name/version/checksum/signature fields, deterministic full-payload verification result, every canonical payload member and content digest, allowed entry modules/modes, sealed destination, payload-manifest digest, interpreter/bootstrap identity, and final-root digest
- **AND** both members boot with controller/module host paths absent and only the sealed capsule payload satisfying package-local imports
- **AND** a mode name alone, pair of runner-file hashes, partial inferred import closure, unverified installed-host import, or missing/extra/drifted payload yields UNKNOWN before analyzer execution.

#### Scenario: Built-in payload remains available after marketplace archive discard

- **GIVEN** the official signed Code Review module was installed and enabled after full-payload checksum/signature verification
- **AND** the downloaded archive and every archive cache entry were deleted as permitted by the marketplace contract
- **WHEN** the analyzer capsule is materialized
- **THEN** `toolchain.py` uses only the loader-registered installed root and re-verifies the identical canonical payload through protected-key and descriptor-relative checks
- **AND** both built-ins boot from the sealed copied payload with no archive fetch, controller-path mount, or host import
- **AND** missing archive bytes do not cause UNKNOWN, while missing/failed loader, origin, checksum, signature, key, root, descriptor, or payload evidence does.

#### Scenario: Generated toolchain lock matches the frozen checkpoint

- **GIVEN** the pre-implementation checkpoint contains the canonical logical toolchain-lock projection and SHA-256
- **WHEN** task 3.12b generates `pr-range-v1-toolchain-lock.json`
- **THEN** every canonical field, byte, and digest equals the frozen projection
- **AND** mismatch invalidates the checkpoint before signing or profile activation
- **AND** the comparison result and identities are appended to `TDD_EVIDENCE.md`.

#### Scenario: Signed OCI acquisition supports fresh and offline capsule materialization

- **GIVEN** a supported environment has no cached OCI blobs, or has a complete controller-owned content-addressed cache
- **WHEN** `toolchain.py` acquires the capsule base rootfs and fixed analyzer wheelhouse before sandbox launch
- **THEN** a fresh acquisition uses only the signed HTTPS registry/repository@manifest-digest locator; every redirect hop/final target remains HTTPS and signed-allowlisted before credentials are attached, the complete ordered chain/status/final URL/credential-sent facts and digest are retained, and config plus ordered layer digest/diff-ID/media-type/size records plus the complete in-image wheel filename/platform/size/SHA-256 manifest are verified before atomic cache publication
- **AND** it never resolves a tag, caller URL, package index, second artifact source, HTTPS downgrade, or unauthorized credential-forwarding target
- **AND** a complete offline cache is accepted only after every blob is rehashed by its digest key
- **AND** a genuine empty-cache materialization installs every selected lock member offline from only `/opt/specfact/wheelhouse` with index access disabled, rejects missing/extra/duplicate/incompatible wheels, and binds the installed RECORD payload back to its wheel digest
- **AND** credentials, cache paths, package indexes, and network are absent from analyzer sandboxes
- **AND** cache miss with unavailable network, partial/mismatched cache, auth/redirect/media/size/timeout/digest failure, unsafe OCI whiteout/tar extraction, or final-root mismatch yields UNKNOWN without alternate-source or host-runtime fallback.

#### Scenario: Python runtime capsule identity is portable across controller storage roots

- **GIVEN** the same signed OCI base and exact analyzer lock are materialized below two different controller storage paths
- **WHEN** their canonical in-capsule `pr-range-v1` identities are verified
- **THEN** OCI manifest/layer, final root-manifest, interpreter/stdlib/extension/loader/library, wheel/RECORD payload, exact version, normalized module/entry-point, and sealed bootstrap identities match
- **AND** generated console-script wrapper bytes and outside-capsule storage paths are excluded from portable distribution identity
- **AND** Python tools launch through the canonical capsule interpreter and sealed bootstrap rather than a host or generated wrapper
- **AND** payload, runtime-file, root-manifest, bootstrap, or entry-point drift is UNKNOWN, while controller storage-root differences do not create false drift.

#### Scenario: Signed toolchain lock closes every runtime dependency

- **GIVEN** `pr-range-v1` is installed for a supported Linux x86_64 CPython 3.11–3.13 environment
- **WHEN** the signed `toolchain-lock-schema-1` resource and fresh installed environment are verified
- **THEN** the lock contains the immutable OCI manifest/layers and fixed wheelhouse manifest plus every evaluated direct and transitive distribution, marker/tag, dependency edge, exact version, wheel/RECORD payload identity, entry point, and canonical closure digest
- **AND** the signed analyzer lock—not host module pip dependencies—contains exact `==` entries for pluggy, nodejs-wheel-binaries, z3-solver, and all other transitive packages
- **AND** host `pip_dependencies` contains no analyzer-only lock member
- **AND** a separately materialized analyzer runtime capsule contains exactly the selected base rootfs, analyzer lock, and bootstrap allowlist; its final manifest seals interpreter, stdlib, extensions, loader/libraries, analyzer/native payloads, and bootstrap while unrelated controller/core/module host files remain outside its namespace
- **AND** unsupported environments, missing/extra analyzer or runtime files, host-path/runtime-mount leakage, marker ambiguity, or OCI/root/edge/version/payload/closure drift yields UNKNOWN before analysis.

#### Scenario: Dependency-bearing project uses an authenticated project runtime

- **GIVEN** selected tests or other closed import-capable members require target project/test dependencies outside the signed analyzer DAG
- **WHEN** the protected target workflow supplies `project-runtime-layer-v1`
- **THEN** its descriptor binds the authorized target commit/tree, explicit dependency-input blobs, Python ABI/platform, exact distribution/native DAG and payloads, immutable OCI/root manifest, and builder/artifact attestation
- **AND** the same read-only layer is used for merge-base and head, while the reviewed project's own code is imported only from each active immutable snapshot
- **AND** a candidate edit to any descriptor-declared dependency input is governed policy impact and UNKNOWN; candidate bytes never rebuild or authorize the layer
- **AND** an attested external first-party dependency is accepted only with its repository/ref/commit/tree and payload identities
- **AND** the project layer cannot provide or shadow pytest, pytest-cov, Coverage, pluggy, the sealed bootstrap, or any analyzer/loader component
- **AND** ordinary selectors importing authenticated dependencies can collect and execute without ambient host packages
- **AND** missing, untrusted, candidate-built, target-input-mismatched, per-side-different, colliding, or import-incomplete runtime evidence produces `error/UNKNOWN`, never NOT_APPLICABLE or host fallback
- **AND** the module producer remains `range_candidate` until the protected consumer independently verifies target/build/artifact provenance and binds it into `pr_range`.

#### Scenario: Infrastructure errors remain distinct from failing evidence

- **GIVEN** one required member reports either a valid completed policy violation or an infrastructure/identity/reconciliation error
- **WHEN** per-member and aggregate statuses are derived
- **THEN** a blocking analyzer finding or valid head-side collected assertion/skip/xfail/xpass outcome records `execution_state=ran`, `evidence_outcome=FAIL`, and aggregate FAIL
- **AND** a baseline non-passing outcome remains per-snapshot FAIL evidence, but the same normalized selector passing at head is classified fixed and does not block
- **AND** unavailable, launch, timeout, unexpected-exit, parse, identity/config, missing-artifact, or reconciliation error records `execution_state=error`, `evidence_outcome=UNKNOWN`, and, when no valid blocker exists, aggregate UNKNOWN
- **AND** both non-shadow aggregates exit 1 and may project legacy FAIL, but the authoritative statuses remain distinct
- **AND** when separate members simultaneously produce valid blocking FAIL and required UNKNOWN, aggregate precedence is FAIL, `has_unknown_required_evidence=true`, and the unknown member evidence remains present.

#### Scenario: Known blocker takes precedence over concurrent uncertainty

- **GIVEN** one required member produces valid completed blocking evidence and another required member produces an infrastructure, identity, artifact, or reconciliation UNKNOWN
- **WHEN** aggregate assurance is derived
- **THEN** assurance_status is FAIL because the blocker is sufficient to disprove acceptance
- **AND** `has_unknown_required_evidence` is true and the unknown member status/diagnostics remain in analyzer coverage
- **AND** the report does not claim complete coverage
- **AND** ledger and signed compatibility consumers receive the same aggregate/status-evidence combination.

#### Scenario: Default PR-range profile has closed membership

- **GIVEN** strict range review resolves the `pr-range-v1` profile
- **WHEN** analyzer coverage is planned
- **THEN** the eight always-required analyzer IDs plus conditional `semgrep-bugs` and `targeted-pytest-coverage` memberships match the normative profile exactly
- **AND** the profile ID, membership, required flags, versions, and policy/config digest are retained in the report
- **AND** no implementation-specific optionality changes assurance.

#### Scenario: Ruff configuration source is unambiguous

- **GIVEN** the authorized target tip contains zero, one, or multiple applicable repository-root Ruff sources from `.ruff.toml`, `ruff.toml`, and `pyproject.toml:[tool.ruff]`
- **WHEN** the controller selects Ruff policy before applicability and launch
- **THEN** zero sources uses explicit `--isolated` and one source uses only its sealed projected `--config`
- **AND** multiple applicable sources produce `ruff_config_ambiguous` UNKNOWN without choosing the more permissive source
- **AND** malformed/unsupported tables or pinned-loader/catalog drift are also UNKNOWN
- **AND** source identities plus the zero/one/multiple decision and digest are bound in producer evidence and independently compared by the protected consumer.

#### Scenario: Ruff analyzes every governed input without cache or per-file silence

- **GIVEN** authorized Ruff policy sets `cache-dir`, `force-exclude=true`, an exclude pattern, or `per-file-ignores`/`extend-per-file-ignores` matching an eligible added or renamed governed file
- **WHEN** the Ruff projection and either immutable-snapshot invocation are built
- **THEN** the controller passes pinned `--no-cache` and `--no-force-exclude`, binds original/effective per-file maps, canonically clears both maps while retaining other authorized rules, and binds projection/option-catalog plus eligible/invoked manifests
- **AND** Ruff analyzes the explicit file without path-specific diagnostic suppression and no cache write targets the snapshot or read-only configuration roots
- **AND** a write, skipped file, non-empty effective per-file map, ineffective transform/flag, or option-catalog drift yields UNKNOWN.

#### Scenario: Ruff cannot change namespace semantics across a rename

- **GIVEN** authorized Ruff policy has `namespace-packages` matching the head directory of identical renamed bytes
- **WHEN** the per-snapshot Ruff projections run
- **THEN** `namespace-packages` is canonically empty and `src` is the active immutable snapshot root on both sides
- **AND** INP001/path-sensitive diagnostics cannot disappear solely because of the rename
- **AND** effective namespace/src mismatch or option-catalog drift is UNKNOWN.

#### Scenario: Ruff cannot change version-sensitive rules across a rename

- **GIVEN** authorized Ruff policy has one global target version and a `per-file-target-version` pattern matching the head side of a pure rename
- **WHEN** the per-snapshot Ruff projections run identical renamed bytes
- **THEN** both projections bind the same global target version and canonically clear `per-file-target-version`
- **AND** the version-sensitive diagnostic remains symmetric across the normalized rename anchor
- **AND** a non-empty effective mapping, newly discovered path-scoped semantic control, or catalog mismatch yields UNKNOWN.

#### Scenario: Pylint cannot ignore a governed input

- **GIVEN** authorized Pylint policy has a whole-file ignore or a no-member exemption matching a governed path, module, class, member pattern, or mixin name
- **WHEN** the per-snapshot Pylint projection is built and invoked
- **THEN** `ignore`, `ignore-patterns`, `ignore-paths`, `ignored-modules`, `ignored-classes`, `generated-members`, `ignore-none`, `ignore-on-opaque-inference`, `ignore-mixin-members`, `ignored-checks-for-mixins`, `mixin-class-rgx`, and `signature-mutators` are canonically empty/disabled, while `contextmanager-decorators` is exactly the pinned built-in allowlist while other non-exemption authorized settings remain bound
- **AND** identical bytes renamed to a formerly ignored module remain diagnostically visible, and the eligible/exact argv manifests match
- **AND** a non-empty effective exemption, unclassified target-specific diagnostic bypass, catalog drift, or manifest mismatch yields UNKNOWN.

#### Scenario: basedpyright cannot ignore a governed input

- **GIVEN** authorized basedpyright policy has restrictive `include`, matching `exclude`, or `ignore` entries that would omit an eligible governed file
- **WHEN** the per-snapshot project artifact is built and invoked
- **THEN** the projection binds the original controls, sets `include` to the sorted exact eligible snapshot-relative file manifest, and canonically clears `exclude`, `ignore`, and path-scoped `strict` while retaining shared global diagnostic settings
- **AND** initial `pr-range-v1` rejects non-empty target `executionEnvironments` before launch
- **AND** invocation uses only the explicit projected project, without positional source arguments, and the eligible/project-include manifests match exactly
- **AND** an include mismatch, non-empty effective exclude/ignore/strict, accepted target execution environment, newly discovered path-scoped diagnostic control, or manifest mismatch yields UNKNOWN.

#### Scenario: basedpyright cannot lower strictness across a rename

- **GIVEN** authorized basedpyright policy has a path-scoped `strict` list or non-empty `executionEnvironments` and identical code is renamed outside its prior path semantics
- **WHEN** authoritative per-snapshot projects are prepared
- **THEN** `strict` is canonically empty and one shared global `typeCheckingMode`/diagnostic policy applies to both sides
- **AND** non-empty target `executionEnvironments` is unsupported UNKNOWN in initial `pr-range-v1`
- **AND** a matching finding whose normalized severity or blocking inputs differ is unknown rather than unchanged.

#### Scenario: Semgrep prohibits per-rule target narrowing and reconciles every pass target

- **GIVEN** a sealed Semgrep bundle contains multiple rules, an eligible governed file, or an eligible file that exceeds the tool's implicit/default target-size limit
- **WHEN** policy validation and either Semgrep pass run
- **THEN** any rule-level `paths.include` or `paths.exclude` control yields unsupported UNKNOWN before launch, including when a different rule would make the pass-level scanned union appear complete
- **AND** for an accepted no-target-narrowing bundle, canonical JSON `paths.scanned` must equal the exact eligible explicit input manifest
- **AND** `paths.skipped` and its reasons remain evidence
- **AND** any missing, extra, oversized, unnormalized, or unreconciled pass path yields UNKNOWN rather than empty PASS.

#### Scenario: Required analyzers handle structurally empty source snapshots

- **GIVEN** an add-only range whose merge-base has no eligible inputs for a required analyzer, or a delete-only range whose head has no eligible inputs
- **WHEN** analyzer coverage is planned for both snapshots
- **THEN** the structurally empty side records NOT_APPLICABLE with its snapshot identity, input class, empty input set, manifest digest, and `absence_reason=no_eligible_inputs_in_snapshot`
- **AND** every opposite side containing eligible inputs still requires a valid analyzer result
- **AND** an adapter's unrecorded empty-file early return is not successful coverage
- **AND** the whole range remains applicable when governed Python exists on either side.

#### Scenario: Targeted pytest distinguishes product failure from infrastructure uncertainty

- **GIVEN** a complete range contains governed runtime-measurable production `.py` whose selected tests may import declared project/test dependencies
- **WHEN** targeted pytest coverage executes with the sealed analyzer capsule plus the identical verified target-tip project-runtime layer on both snapshots
- **THEN** the profile records the planned selector digest, exact per-selector JUnit outcomes/counts, runner/environment identities, JUnit digest, and coverage artifact digest
- **AND** only an exact head set where every selected test collects once, executes, and passes satisfies the member
- **AND** assertion failure or selected head skip/xfail/xpass produces FAIL
- **AND** missing/untrusted/mismatched project-runtime evidence, reserved runner collision, dependency import failure, ambient-host access, unavailable pytest, timeout, collection/internal/usage error, unexpected no collected tests, missing/duplicate/deselected selected tests, reconciliation mismatch, or missing/unreadable coverage produces UNKNOWN
- **AND** only a manifest-proven absent-side input/selector produces NOT_APPLICABLE for that side
- **AND** the stage cannot be omitted by `--no-tests`.

#### Scenario: Coverage reconciles every runtime-measurable production input

- **GIVEN** an applicable snapshot contains tracked regular governed production `.py` paths and may also contain governed `.pyi` stubs in its immutable selected-input manifest
- **WHEN** targeted coverage produces a readable artifact under the authorized target policy
- **THEN** `runtime-measurable-production-v1` normalizes and binds a sorted coverage-file manifest of canonical repository-relative `.py` paths plus a separate sorted static-only `.pyi` manifest
- **AND** every runtime-measurable production `.py` path present in that snapshot appears exactly once before threshold evaluation
- **AND** each governed `.pyi` is absent from Coverage reconciliation but remains exactly once in every applicable static analyzer's eligible and invoked manifests
- **AND** a `.pyi`-only side records targeted pytest/coverage as NOT_APPLICABLE with the classifier and empty runtime manifest, never PASS or UNKNOWN merely because Coverage cannot measure stubs
- **AND** a target-policy `source`, `include`, or `omit` rule that leaves any such path absent produces `error/UNKNOWN`, even if tests pass and the reported threshold is satisfied
- **AND** duplicate, escaping, ambiguously aliased, or path/content-mismatched entries also produce `error/UNKNOWN`
- **AND** a governed path absent from that commit side is recorded with immutable absence evidence and is not required in that side's artifact.

#### Scenario: Completed coverage-threshold failure is semantic FAIL

- **GIVEN** every planned selector collects once and passes and the sealed coverage artifact is valid and reconciled
- **WHEN** measured coverage is below the sealed effective threshold
- **THEN** targeted coverage records `execution_state=ran`, `evidence_outcome=FAIL`
- **AND** evidence binds the configured threshold, measured total/per-file values, configuration and artifact digests, and semantic process exit
- **AND** missing/unreadable/unreconciled measurement remains `error/UNKNOWN`
- **AND** a baseline threshold FAIL followed by head threshold PASS under identical policy is fixed and non-blocking, while head threshold FAIL blocks.

#### Scenario: Delete-only production runs the complete head suite

- **GIVEN** a range deletes governed runtime-measurable production `.py`
- **WHEN** `complete-pytest-suite-v1` plans the head side
- **THEN** the planner collects and executes the complete selector inventory recognized by the sealed head pytest policy without any per-source mapping
- **AND** every normalized baseline selector absent from head is `removed_selector` UNKNOWN
- **AND** every head selector collects exactly once and executes against the head snapshot
- **AND** delete-only production cannot make the head member NOT_APPLICABLE merely because the deleted source is absent there.

#### Scenario: Repaired baseline test is fixed evidence

- **GIVEN** a normalized planned selector has a valid non-passing result at merge base and collects exactly once and passes at head
- **WHEN** targeted pytest evidence is aggregated
- **THEN** the baseline result remains per-snapshot FAIL evidence
- **AND** the pair is classified `fixed` and is non-blocking
- **AND** the baseline failure does not override the exact passing head result or force aggregate FAIL
- **AND** infrastructure or selector-reconciliation uncertainty on either side remains UNKNOWN.

#### Scenario: Test-only Python range executes the complete suite

- **GIVEN** a range changes or adds governed Python tests without changing production Python
- **WHEN** `complete-pytest-suite-v1` plans both sides
- **THEN** it records and digests the complete merge-base and head selector inventories recognized by the sealed policy, including multiple and nonconventionally named collected test files
- **AND** it normalizes only recorded pure one-to-one file renames, executes every head selector, and reconciles the full set difference
- **AND** a failing changed-test assertion yields FAIL even when static analyzers are clean
- **AND** any normalized baseline selector missing at head, deleted test, or changed test path that is neither collected nor classified test-support yields UNKNOWN
- **AND** the member is never NOT_APPLICABLE merely because production Python did not change.

#### Scenario: Test roles are frozen before collection

- **GIVEN** a governed path was a collected test module at merge base and the head makes it empty, sets module-level `__test__ = False`, moves it outside the sealed collection roots, or renames it to a basename that no longer matches the authorized `python_files` policy
- **WHEN** `complete-pytest-suite-v1` classifies inputs and collects both snapshots
- **THEN** `pytest-input-role-v1` uses only immutable paths plus the shared authorized target-tip `testpaths`/root-default and `python_files` policy before collection
- **AND** it reproduces pinned pytest 9.0.3 `_pytest.pathlib.fnmatch_ex` on the same materialized absolute path: basename matching for separator-free patterns and full-path matching with `*/` prefixing for relative path-bearing patterns
- **AND** `python_files = tests/unit/test_*.py` classifies an empty `tests/unit/test_new.py` as a test candidate and therefore UNKNOWN when it contributes no selector
- **AND** contents, AST, `__test__`, marks, decorators, and observed selector counts cannot reclassify a test candidate as support
- **AND** the missing head selector is `uncollected_changed_test` UNKNOWN, and a test-candidate-to-support/outside-root role transition is also UNKNOWN
- **AND** only `conftest.py` or a non-test-pattern helper frozen below a collection root before collection may be support without its own selector
- **AND** both role manifests, policy/classifier digest, and transition are bound as evidence.

#### Scenario: Head cannot neutralize selected tests with pytest outcomes

- **GIVEN** a planned head selector is changed to skip, xfail, xpass, or become deselected
- **WHEN** targeted pytest coverage reconciles the exact selector set with JUnit
- **THEN** skip, xfail, or xpass is FAIL rather than passing coverage
- **AND** deselected, missing, duplicate, or count-mismatched selectors are UNKNOWN
- **AND** an exit-zero pytest process and readable coverage artifact cannot override those outcomes
- **AND** only exactly-once collected and passed selectors satisfy the head member.

#### Scenario: Complete suite handles an entirely absent merge-base input class

- **GIVEN** a range creates the repository's first governed runtime-measurable production `.py` input and first governed tests so the merge-base contains no governed runtime-measurable production `.py`, test, or test-support input
- **WHEN** `complete-pytest-suite-v1` is evaluated for both snapshots
- **THEN** the merge-base side records NOT_APPLICABLE with complete empty input/selector manifests and `absence_reason=no_eligible_inputs_in_snapshot`
- **AND** it is not executed as an empty pytest selection
- **AND** the head side still requires complete collection, exactly-once passing execution, and a valid coverage artifact
- **AND** if the merge-base contains any other governed production/test/test-support input, its complete recognized suite runs rather than using this absence exception.

#### Scenario: Every pinned Pylint configuration source is governed

- **GIVEN** the candidate changes any Pylint source recognized by the exact pinned loader, including setup.cfg/tox.ini sections or pylintrc TOML variants
- **WHEN** policy impact and target-tip configuration are resolved
- **THEN** the path/section change is present in the governed policy manifest and a policy-only range is UNKNOWN
- **AND** exactly zero or one effective target-tip Pylint source is allowed; multiple sources are `pylint_config_ambiguous` UNKNOWN
- **AND** the selected source or sealed default is passed explicitly through `--rcfile` with source discovery disabled
- **AND** a candidate Pylint config cannot weaken current analysis or be misclassified NOT_APPLICABLE.

#### Scenario: Pylint cannot load repository analyzer-extension code

- **GIVEN** the authorized Pylint policy contains any canonical alias of non-empty `init-hook`, `extension-pkg-allow-list`, or deprecated `extension-pkg-whitelist`, or names a plugin outside the signed profile plugin manifest
- **WHEN** `pr-range-v1` validates profile safety before applicability and prepares both analyzer sides
- **THEN** the member is UNKNOWN before Pylint launch and no hook/plugin/extension code is imported
- **AND** an unsafe extension option cannot become NOT_APPLICABLE in an otherwise extension-only or no-governed-Python range
- **AND** the initial profile's empty plugin manifest rejects every `load-plugins` entry
- **AND** repository-local, unresolved, duplicate, wildcard, path-mutating, or unapproved plugins cannot participate in differential comparison
- **AND** a future accepted plugin requires a new signed profile version binding distribution/module/version/content-manifest identity identically on both sides
- **AND** CR14 does not infer arbitrary Python plugin or init-hook import closure.

#### Scenario: Candidate coverage configuration cannot suppress measurement

- **GIVEN** the candidate changes coverage or pytest policy to exclude governed source, redirect coverage data, or inject a different cov-config
- **WHEN** targeted pytest/coverage runs
- **THEN** the policy change is governed UNKNOWN and cannot make the range NOT_APPLICABLE or PASS
- **AND** runtime uses only the sealed target-tip pytest/coverage projection or generated pinned default through explicit `-c` and `--cov-config`, with coverage selected from the complete pinned 7.15.4 source set including `.coveragerc.toml`
- **AND** candidate/environment auto-discovery is disabled and the effective options plus projection digests are verified
- **AND** a candidate `exclude_also = [".*"]` cannot turn uncovered source into zero statements or 100% passing coverage
- **AND** ambiguity, override, projection, or integrity mismatch is UNKNOWN.

#### Scenario: Target coverage regex cannot suppress measurement

- **GIVEN** the authorized target Coverage policy defines a non-empty `exclude_lines`, `exclude_also`, `partial_branches`, or `partial_also` pattern that candidate code could match
- **WHEN** strict targeted coverage policy is projected
- **THEN** `coverage-exclusions-disabled-v1` yields `coverage_exclusion_policy_unsupported` UNKNOWN before launch
- **AND** with absent/empty target fields, the projection explicitly clears pinned Coverage 7.15.4 built-in exclusion/partial-branch defaults and additive lists
- **AND** original/effective normalized lists plus schema/transform/projection digests are evidence
- **AND** a matching custom marker cannot create a baseline-threshold-FAIL/head-PASS false fix
- **AND** unclassified aliases, loader drift, or ineffective clearing is UNKNOWN.

#### Scenario: Every pinned pytest configuration source follows pinned precedence

- **GIVEN** the authorized target tip contains one or more pytest configuration sources supported by pinned pytest 9.0.3
- **WHEN** targeted pytest policy is selected
- **THEN** the complete closed source/section set is manifested and the first matching source is selected using the signed pinned-loader order
- **AND** present zero-byte `pytest.toml`/`.pytest.toml` and `pytest.ini`/`.pytest.ini` sources are active and suppress every lower-precedence source
- **AND** a table-free `pyproject.toml` is selected only as the final fallback when no earlier source matches
- **AND** ignored lower-precedence sources remain evidence and candidate changes to any supported source remain governed impact
- **AND** native `[tool.pytest]` and legacy `[tool.pytest.ini_options]` are mutually exclusive in one primary pyproject match
- **AND** an unsupported table, dual table, parse failure, or loader/profile/source-order drift yields UNKNOWN.

#### Scenario: Authorized pytest policy cannot narrow the complete inventory

- **GIVEN** the authorized target pytest policy contains `addopts` such as `--ignore=tests/ignored`, `--ignore-glob`, `--deselect`, `-k`, `-m`, `--last-failed`, `-x`, `--maxfail`, stepwise, a config/root/plugin override, or a target pytest-cov control
- **WHEN** the sealed per-side pytest policy is projected for a production-only range
- **THEN** `pytest-selection-controls-disabled-v1` parses aliases and values with the complete pinned pytest 9.0.3 plus pytest-cov option catalog before collection
- **AND** every collection/cache selector, execution short-circuit, discovery/plugin override, positional selector, and coverage override yields `pytest_selection_policy_unsupported` UNKNOWN rather than a filtered PASS
- **AND** an ignored failing `tests/ignored/test_failure.py` plus a visible passing test cannot produce a passing complete inventory
- **AND** declarative `testpaths` and `python_files` remain bound suite identity, while only catalogued non-selecting addopts survive before controller-owned argv
- **AND** an unknown/plugin-added option or parser/help/catalog drift is UNKNOWN.

#### Scenario: Effective pytest configuration cannot hide candidate modules

- **GIVEN** the authorized target pytest configuration sets non-empty `norecursedirs = ignored` and a production-only range leaves one passing visible test plus one failing test below `tests/ignored`
- **WHEN** the per-side sealed policy and role/collection manifests are reconciled
- **THEN** the complete pinned pytest/pytest-cov `addini` catalog classifies `norecursedirs` as `selection_filter` and yields `pytest_selection_policy_unsupported` UNKNOWN before collection
- **AND** every other effective ini/TOML field is classified and bound; unknown or plugin-added fields and catalog drift are UNKNOWN
- **AND** independently, every path classified as `test_candidate` must contribute a selector on each extant side, so whole-file omission by config or collection hook is `uncollected_test_candidate` UNKNOWN
- **AND** the visible passing selector and valid coverage cannot convert either uncertainty to PASS.

#### Scenario: Pytest paths resolve against each immutable source snapshot

- **GIVEN** selected target pytest policy contains relative path settings and an imported dependency differs between merge base, head, and caller checkout
- **WHEN** targeted pytest executes both source snapshots
- **THEN** every pinned-schema path field, including `pythonpath` and `testpaths`, is rewritten into a separate side-specific projection
- **AND** each invocation passes explicit side `-c` and `--rootdir <side-snapshot-root>`
- **AND** merge-base imports merge-base bytes and head imports head bytes, never projection-directory or caller-checkout bytes
- **AND** the report binds the shared logical transform identity plus side root substitutions/output digests
- **AND** absolute, escaping, unsupported, missing, or integrity-mismatched paths yield UNKNOWN.

#### Scenario: Pytest writes only to process-private roots

- **GIVEN** selected target pytest policy or trusted addopts names writable `cache_dir`, `log_file`, basetemp, JUnit, or another pinned output path
- **WHEN** separate side projections are generated
- **THEN** every pinned path field/token is classified as read/source or write/output
- **AND** writable paths are replaced with deterministic role-specific process-private cache/temp/output destinations while the controller-owned JUnit path wins
- **AND** original values, roles, substitutions, effective paths/globs, schema/map/projection/argv digests, and integrity are evidence
- **AND** snapshots and config mounts remain read-only and receive no pytest writes
- **AND** unclassified outputs, outside-root writes, collisions, unexpected output, or ineffective transformation is UNKNOWN.

#### Scenario: Every pinned coverage source follows pinned precedence

- **GIVEN** the authorized target tip contains `.coveragerc.toml` or multiple sources recognized by Coverage 7.15.4
- **WHEN** targeted coverage policy is selected
- **THEN** `.coveragerc`, `.coveragerc.toml`, setup.cfg, tox.ini, and pyproject.toml recognized sections are all manifested
- **AND** the first applicable source is selected using the signed pinned-loader order and ignored lower-precedence sources remain evidence
- **AND** candidate changes to any supported source remain governed policy impact
- **AND** parse/shape failure or loader/profile/selection drift yields UNKNOWN.

#### Scenario: Coverage cannot load repository plugin code

- **GIVEN** selected Coverage policy configures one or more `[run] plugins`
- **WHEN** targeted coverage is prepared
- **THEN** the initial empty signed Coverage plugin manifest makes the member UNKNOWN before launch
- **AND** repository, unresolved, duplicate, wildcard, or unapproved plugin modules are never imported from either snapshot
- **AND** a future accepted plugin requires a new signed profile version binding distribution/module/version/payload identity identically on both sides
- **AND** CR14 does not infer arbitrary Coverage plugin import closure.

#### Scenario: Coverage writes only to its process-private output root

- **GIVEN** selected Coverage policy declares relative or absolute writable paths such as `[run] data_file = logs/tests/coverage/.coverage`
- **WHEN** a per-process coverage projection is generated
- **THEN** every pinned-schema writable data/debug/report field and pytest-cov report destination is replaced with a deterministic role-specific private-output path
- **AND** original values, field roles, root substitutions, effective paths/globs, generator/schema/map/output digests, argv, and integrity are evidence
- **AND** the read-only snapshot and config mounts remain read-only inputs and receive no Coverage writes
- **AND** unclassified fields, paths outside the private root, collisions, unexpected outputs, or transformation mismatch yields UNKNOWN.

#### Scenario: Ruff transitive extend policy is governed and sealed

- **GIVEN** the authorized target Ruff config extends another repository config, which may itself extend another config
- **WHEN** policy impact and Ruff input are resolved
- **THEN** the controller resolves the complete target-tip closure, manifests every ordered node/edge/path/blob/content digest, and materializes only that preserved-layout closure read-only
- **AND** a candidate change to any target-closure member is governed UNKNOWN rather than NOT_APPLICABLE
- **AND** both snapshots use the same sealed target closure through explicit `--config`
- **AND** absolute, escaping, symlink, missing, cyclic, duplicate-canonical, unsupported, or over-bound closure input yields UNKNOWN without Ruff source-tree discovery.

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

