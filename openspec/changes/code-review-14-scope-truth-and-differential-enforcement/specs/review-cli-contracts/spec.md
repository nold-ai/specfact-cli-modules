## ADDED Requirements

### Requirement: Truthful Review Assurance Status

The governed review report schema `1.6` SHALL expose authoritative `assurance_status` as `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE` plus derived `has_unknown_required_evidence`. `WAIVED` SHALL be a governance overlay, not a verifier-produced status. NOT_APPLICABLE SHALL require successfully resolved no-governed-impact evidence. Otherwise aggregate precedence is FAIL for any validated blocker, UNKNOWN only when required uncertainty exists without a known blocker, and PASS only when neither exists. A mixed FAIL/UNKNOWN report SHALL retain every unknown member and set the derived flag while aggregate remains FAIL.

#### Scenario: Mandatory evidence is unknown

- **GIVEN** scope or a mandatory analyzer is unknown and no valid completed blocker already proves FAIL
- **WHEN** enforce-mode reporting completes
- **THEN** assurance is UNKNOWN and process exit is non-zero
- **AND** partial facts/findings remain available
- **AND** the human summary does not say all validations passed.

#### Scenario: No-governed-impact report binds the activated suppression catalog

- **GIVEN** immutable scope resolution proves no governed impact
- **WHEN** the producer emits schema 1.6 NOT_APPLICABLE evidence without launching analyzers
- **THEN** the report still activates and binds the authenticated suppression-catalog digest
- **AND** missing or mismatched catalog identity changes the report to UNKNOWN rather than emitting an incomplete NOT_APPLICABLE report.

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
- **AND** when the declared Requirements bundle is unavailable, attachment fails with the governed run-command validation error rather than an unhandled import traceback.

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
- **AND** that legacy staged-line calculation accepts file headers only in Git file-metadata state, never from paired `---`/`+++` hunk content
- **AND** unavailable cached-diff evidence preserves every legacy blocking finding instead of treating the staged change set as empty
- **AND** cached-diff discovery ignores inherited repository/index redirect variables so evidence always comes from the governed repository and index
- **AND** the helper remains `explicit_files` and does not claim `pr_range`.

#### Scenario: Exact advertised core runtime loads schema 1.6

- **GIVEN** a candidate Code Review package proposes `core_compatibility: '===0.55.1'`
- **WHEN** the pre-release compatibility gate runs in a fresh environment
- **THEN** it checks out immutable lightweight core tag `v0.55.1` at full commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` and full tree `47984be5434d7ae65ed6908bf525a32053290337`, installs that core plus the candidate module package, loads the module through core, derives `verified-candidate-module-payload-v1` from immutable candidate git/package/workflow evidence, and validates every schema 1.6 consumer-matrix status/projection
- **AND** candidate identity is confined to this pre-release smoke and cannot be accepted as official marketplace-install provenance or protected `pr_range` assurance
- **AND** the gate rejects ordinary `==0.55.1`, PEP 440 local/alternate strings such as `0.55.1+vendor`, `>=0.55.1,<1.0.0`, a wildcard, or any specifier admitting an untested core identity
- **AND** an unavailable or mismatched identity, branch fallback, install/load failure, or matrix failure blocks release and the compatibility declaration
- **AND** this smoke proves exact-version load/schema interoperability only; protected PR-context verification remains the separate downstream core adoption contract
- **AND** a later module metadata release may advertise a newly released exact paired-core version only after its immutable tag/commit/tree passes the same matrix smoke.

#### Scenario: Legacy enforcement mode is policy, not scope

- **GIVEN** schema 1.6 dual-writing is enabled
- **WHEN** enforcement and scope are serialized
- **THEN** request mode enforce normalizes to legacy enforcement_mode full
- **AND** an omitted enforcement option with range scope normalizes to strict full, while omission on the deprecated changed/worktree path retains changed
- **AND** full, changed, and shadow retain their legacy values when explicitly valid
- **AND** changed mode is accepted only with the deprecated changed/worktree compatibility path
- **AND** explicit range plus changed mode is rejected
- **AND** strict range writes enforcement_mode full, shadow range writes shadow, and scope_evidence alone identifies range.

#### Scenario: Local capsule reports preserve scope truth and changed-line policy

- **GIVEN** a local capsule review resolves the default or deprecated changed scope, explicit full scope, or positional files
- **WHEN** the capsule report is serialized
- **THEN** `scope_evidence.assurance_kind` is respectively `worktree`, `full`, or `explicit_files`
- **AND** the capsule runtime boundary rejects every other assurance kind before runtime preparation or report construction, so a type-checking annotation alone cannot admit unsupported provenance
- **AND** the selected enforcement mode remains independent from that scope identity
- **AND** changed enforcement blocks only blocking findings on changed lines while retaining unchanged-line blockers as advisory evidence
- **AND** when every blocking finding reported by a failing analyzer member is proven outside changed lines, serialized member evidence retains `pre_enforcement_evidence_outcome=FAIL`, projects authoritative `evidence_outcome=PASS`, and records the unchanged-blocker advisory disposition without removing the findings
- **AND** a failing analyzer member without corresponding proven-unchanged blocking evidence remains `FAIL`; changed enforcement never invents a passing member outcome from an unexplained failure
- **AND** JSON model validation and first-party ledger ingestion preserve the same changed-mode `PASS` or `PASS_WITH_ADVISORY` projection and exit `0` instead of reinterpreting it as `UNKNOWN`
- **AND** unavailable changed-line discovery, including Git diff failure or incomplete untracked-file evidence, cannot downgrade a completed `FAIL` or required `UNKNOWN` report, while a completed blocker-free report retains its existing pass state
- **AND** Git-quoted path headers, including UTF-8 and control-character filenames in worktree or cached diffs, are decoded to the exact filesystem path or make changed-line evidence unavailable
- **AND** unquoted Git path headers preserve trailing filename whitespace while removing only Git's header delimiter
- **AND** changed-line Git commands force canonical `a/` and `b/` diff prefixes independently of ambient mnemonic, no-prefix, or custom-prefix configuration
- **AND** tracked diff paths and analyzer findings are lexically normalized from repository-root or absolute identity to one caller-working-directory identity, including nested invocations, parent-repository files, and redundant relative segments, without following symlinks before changed-line matching
- **AND** ordinary worktree analysis rejects selected symlinks and directories before analyzer execution, binds the pre-analysis raw selected regular-path states plus tracked, non-ignored untracked, analyzer-relevant ignored policy/source/test-support paths, contained symlink targets, and immutable `HEAD` tree identity or the format-correct empty tree when `HEAD` is proven unborn, and admits an unselected symlink or directory only when its raw identity plus every lexical and terminal path component remains beneath that same bound repository root; it uses the same base tree for raw and Git changed-line evidence and verifies the complete identity after analysis and changed-line projection; the bound input set includes ignored analyzer configuration, imported source, and test-support paths exposed by the repository-root snapshot, so their byte, presence, path-type, target, or set drift returns required `UNKNOWN` / exit `1` rather than mixed-member or stale clean evidence, while a stable unselected gitlink directory remains bindable; when explicit selected files are proven outside any repository, the same checks bind their exact absolute raw path states without a tree component
- **AND** ordinary worktree changed-line evidence is corroborated against raw filesystem bytes and raw committed or proven-empty base-tree blobs, so clean filters and `assume-unchanged` or `skip-worktree` index hints cannot hide analyzer-visible changes; disagreement makes changed-line evidence unavailable rather than treating the file as unchanged
- **AND** cached changed-line enforcement disables Git replacement objects, freezes one immutable stage-zero index tree together with an unchanged base-tree identity and caller coordinate, uses the empty tree as the immutable base before the first commit, materializes analyzer input directly from its raw blobs without clean, smudge, text-conversion, or export-attribute filters, rebases capsule and development-host findings from that repository-root snapshot to the frozen caller coordinate, runs any development-host fallback from the materialized root, binds the root plus every logical directory type/device/inode identity during construction, requires every materialized symlink's immediate lexical target and complete terminal resolution to remain beneath that root, verifies those no-symlink directory identities, every-hop symlink containment, and every materialized blob before analysis and again after host analysis, derives changed-line evidence only from the frozen base/index tree pair, and emits required `UNKNOWN` / exit `1` when materialization, a selected symlink or gitlink, an escaping or leave-and-re-enter direct/chained support symlink, an extant selected path absent from the staged tree, filesystem case/Unicode identity, post-analysis identity, or line evidence is unavailable or ambiguous, so index flags, replacement refs, nested invocation, and worktree, analyzer, external-target, or live-`HEAD` mutation cannot change or reclassify the reviewed snapshot
- **AND** machine-parsed Git diffs force raw text output and disable color and text-conversion drivers so repository attributes or ambient configuration cannot hide protocol headers
- **AND** reviewed filenames are passed to diff and untracked-file discovery as literal pathspecs so legal pathspec syntax in a filename cannot change the evidence query
- **AND** an explicitly reviewed untracked file remains fully changed even when repository ignore rules match it; ignore filtering cannot erase caller-selected line evidence
- **AND** destination headers are accepted only in file-header state, never from added hunk content, so later hunks retain the exact reviewed file identity
- **AND** changed-line Git commands ignore repository-local redirect variables such as `GIT_DIR`, `GIT_INDEX_FILE`, and `GIT_WORK_TREE`
- **AND** untracked-file discovery treats only empty Git output as absence and never trims a non-empty path identity to absence
- **AND** incomplete required capsule evidence remains `UNKNOWN` with a non-zero exit under changed enforcement and is never rewritten to PASS.

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

Static CLI contract fixtures SHALL cover argv parsing and serialized report/error contracts for worktree, index, range, full, positional files, deprecated changed alias, required full refs, assurance/enforcement status projection, positional PR-range downgrade rejection, and invalid option combinations. Stateful Git content/topology behavior—staged-versus-unstaged index content, unique merge-base selection with advanced-base-tip and criss-cross/multiple-best-base cases, changed-test inclusion, empty range, Git failure, immutable materialization including regular-blob mode/no-follow and symlink-mode-change rejection, merge-base/head classifications, and analyzer identity/coverage—SHALL be proved only in the allowlisted scope/differential unit and end-to-end tests that create isolated temporary repositories.

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
- **AND** the protected-CI alternative is `--scope range --base-ref <full-ref> --head-ref <full-ref> --pr-context-file <runner-temp-file> --enforcement full`, with any applicable target-tip project-runtime descriptor/attestation bound inside that immutable context
- **AND** the producer result with matching claimed context is `range_candidate`, while the same local command without context is `range_preview`; neither is merge authority without the protected verification envelope
- **AND** positional files remain valid for explicitly labelled non-PR `assurance_kind=explicit_files` runs.

#### Scenario: Canonical repository merge guidance uses complete PR range

- **GIVEN** a developer or agent follows the mandatory repository quality gate, module/bundle guide, or generated Code Review instructions
- **WHEN** the guidance describes merge or pull-request assurance
- **THEN** protected CI uses `--scope range`, full base/head identities, an event-derived `--pr-context-file` outside the checkout that also binds any applicable authenticated target-tip project-runtime layer, and `--enforcement full`
- **AND** the producer emits `assurance_kind=range_candidate`, never pr_range
- **AND** the protected consumer independently enumerates all best merge bases, requires exactly one expected merge base, then derives the complete governed diff, selected Python files/lines, governed policy path/section manifests and candidate-policy-change digest, object-type/Git-mode/status/rename/deletion manifests, authorized target-tip policy/config selection, declared project-runtime source-lock inputs, and any applicable project-runtime builder/artifact attestation; requires approved signed producer module/schema/profile/toolchain plus workflow/job/artifact provenance; then compares every identity and digest with the immutable report
- **AND** its envelope binds every compared identity/manifest/digest and rejects any omitted governed Python or policy input, or merge-base, diff, selection, rename/deletion, policy/config, project-runtime input/build/artifact, producer, or artifact mismatch as UNKNOWN
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
