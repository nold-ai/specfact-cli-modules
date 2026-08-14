## Context

Review quality is bounded first by whether the intended code was actually analyzed. A PR reviewer evaluates committed base-to-head behavior, whereas worktree scope evaluates local uncommitted edits. Both are useful, but they are different facts and must never share an ambiguous green label.

## Goals and Non-Goals

### Goals

- Resolve an explicit immutable scope before analyzers run.
- Represent failure to resolve scope or mandatory tools as `UNKNOWN`.
- Compare base and head under identical analyzer identities.
- Distinguish introduced, fixed, unchanged, and unknown findings.
- Keep tests/configuration visible in PR evidence by default.
- Separate severity, finding lifecycle, autofix availability, and policy.

### Non-Goals

- Invent more detectors or open-ended semantic judgments.
- Turn heuristics or AI hypotheses into deterministic blockers.
- Merge Requirements and review verdicts.
- Replace full tests, contracts, security, or human review.

## Decisions

### Replace ambiguous changed scope with explicit sources

The CLI accepts:

- `--scope worktree`: tracked changes relative to HEAD plus untracked eligible files;
- `--scope index`: the exact staged/index blob snapshot relative to HEAD, materialized independently from later unstaged worktree edits;
- `--scope range --base-ref <full-ref> --head-ref <full-ref>`: committed merge-base-to-head delta;
- `--scope full`: all eligible repository files;
- positional files: one explicit caller-selected set labelled `scope_evidence.assurance_kind=explicit_files`; it is not pull-request range evidence.

`--scope changed` remains one-release deprecated compatibility for `worktree` and prints a warning. A PR assurance consumer requires `scope_evidence.assurance_kind=pr_range` and rejects worktree, index, full, changed-alias, or positional-file evidence. Explicit files remain valid for local/manual enforcement when no PR-range claim is made.

Range resolution records full base, head, and merge-base commit/tree SHAs; diff/path digest; selected file and line facts; rename/deletion facts; filters/facets; repository root; command request; resolver version; assurance kind; and diagnostics. Tests are included by default. Explicit facet exclusion is recorded and cannot be mistaken for analyzed evidence.

### Bind analysis to immutable commit content

`scope.py` is the only Git boundary. For index mode it SHALL materialize the exact staged blobs and declared staged configuration from the Git index outside the caller worktree, record the index tree/blob identities, and analyze those bytes even when the same pathname has additional unstaged edits. Unmerged entries, intent-to-add entries without content, or unreadable index objects yield `UNKNOWN`.

For range mode it SHALL materialize fresh, detached baseline and head roots outside the caller worktree. The baseline root is the resolved merge-base commit/tree; the supplied base-ref tip is recorded only as a resolver input and SHALL NOT be analyzed as the PR baseline. The head root is the resolved head commit/tree. For each snapshot, `scope.py` SHALL build a manifest of repository-relative path, Git blob identity, and content digest for every selected analyzer input and every declared analyzer-configuration input. The runner receives only paths rooted in the appropriate materialization and runs the merge-base/head snapshots with the same pinned analyzer/toolchain and trusted policy/config digest.

The trusted policy/config identity is resolved once from the exact authorized target base-ref tip and applied to both range source snapshots. The trusted PR/merge-queue integration provides an `expected_target_tip` record with provider, repository, target ref, PR/queue identity, full commit SHA, and tree SHA. The producer requires exact equality with the resolved base-ref tip and binds a canonical context digest; a standalone caller cannot self-assert this trust. The consuming gate independently compares the report with its own event context before accepting `pr_range`. A mismatched, moved, untrusted, missing, or unreadable target identity or policy makes the run UNKNOWN. `scope.py` materializes the target-tip policy bundle separately from both source roots and records its commit/tree plus every selected config path/blob/digest. The merge base remains the source-code comparison baseline; using current target policy does not turn target-only source commits into differential inputs. `runner.py` passes the sealed bundle through one invocation context; configurable adapters MUST NOT discover policy from either analyzed source root, the caller worktree, or process `.`.

The exact adapter boundary is:

- Ruff receives the selected target-policy Ruff config with explicit `--config`, or `--isolated` when no governed config exists.
- Pylint receives an explicit target-policy `--rcfile`; absence uses a sealed pinned-default config and disables source-tree discovery.
- basedpyright receives a distinct per-snapshot projected `--project` artifact; it never uses `--project .` or points directly at the target-policy bundle. Using the pinned basedpyright configuration schema, source-relative fields (including nested execution-environment roots/extra paths) are rewritten to the corresponding immutable source root, while `venvPath`/`venv` bind to the same sealed toolchain environment. Original policy, projection map, and projected-config digests are evidence. Unsupported path semantics, path escape, caller/policy-bundle source lookup, or missing projected dependencies yield `UNKNOWN`.
- Semgrep and the conditional bug pass resolve only from the explicit target-policy bundle already represented by their `bundle_root` seam.

The shared comparison identity is identical across sides and contains analyzer/toolchain identities, trusted target-policy/config source digest, projection algorithm/schema identity, and a canonical logical projection-map digest using symbolic source/toolchain roots. Per-snapshot projected-config digests are separate materialization evidence and may differ because absolute merge-base/head roots differ. Classification compares the shared identity, then validates each projection against its logical map; it never requires raw projected-config digest equality. A missing/unreadable selected config or any adapter that cannot honor explicit configuration makes coverage `UNKNOWN`. Candidate analyzer-config changes remain visible in scope evidence but cannot authorize or weaken their own comparison; they run only as separately labelled shadow evidence until promoted. If a newly promoted target policy cannot be projected safely onto the older merge-base snapshot, assurance is UNKNOWN and the branch must be rebased rather than falling back to older or head-discovered configuration.

Every range-side analyzer receives a `SnapshotInvocationContext` binding commit/tree/root, `cwd`, manifest-bound import roots, sealed non-editable toolchain/dependency environment, sanitized environment, external output root, and digest. Subprocesses run from the active snapshot root; inherited caller/worktree/policy-bundle import paths, `PYTHONPATH`, `PYTHONHOME`, editable-source roots, user site, and startup hooks are removed. Only that snapshot's declared import roots and the same sealed toolchain dependencies are added. Pytest plugin autoload is disabled and only pinned declared plugins are enabled. Pylint init hooks, CrossHair, targeted pytest, and every other import-capable analyzer must consume this context. Any caller-source import, undeclared plugin/root, or context mismatch is `UNKNOWN`.

Before and after each snapshot analysis, the resolver SHALL verify the selected-input manifest. A missing object, path escape, content mismatch, cleanup failure that prevents verification, or post-analysis mutation yields `UNKNOWN` with diagnostics. Index and range modes SHALL reject `--fix`, `--preview-fixes`, and `--with-mutation` before materialization. Those operations require a separate worktree/explicit-file run and cannot be attached to index-snapshot or PR-range assurance. Range mode and `assurance_kind=pr_range` are reserved for the complete governed merge-base-to-head Python selection. Validation SHALL reject `--exclude-tests`, any `--focus` facet (`source`, `tests`, `docs`, or `simplify`), `--path`, `--no-tests`, and `--level` before materialization because each drops governed files, analyzer/test evidence, or reported findings. `--include-tests` is redundant but compatible. Filtered review remains available only as a separately labelled worktree or explicit-file run; this change does not introduce a partial-range assurance kind.

### Empty and unresolved are different

A successfully resolved range with zero governed Python files is `NOT_APPLICABLE`. A missing ref, shallow history, Git error, timeout, repository mismatch, or parsing failure is `UNKNOWN`. Enforce mode exits non-zero for unknown; shadow may exit zero but must preserve the unknown report/status.

### Use symmetric merge-base/head analysis

Range review evaluates the resolved merge-base snapshot and head snapshot with the same analyzer version, configuration digest, policy, and normalization. The current base-ref tip participates only in merge-base resolution; target-branch commits after divergence are never treated as the PR baseline or classified as feature-branch fixes. Stable fingerprints use analyzer/rule, semantic file anchor, symbol/region identity, and normalized message fields. Before fingerprint comparison, a head finding under the new side of a resolved one-to-one Git rename SHALL use that rename's old/base path as its canonical file anchor; the original head path and rename fact remain evidence. Copies and unpaired additions are not rename-normalized. Exact implementation may vary by tool but line-number equality alone is insufficient.

Each head finding is classified `introduced`, `unchanged`, or `unknown`; missing head fingerprints matched at base are `fixed`. Changed lines are supporting evidence, never the sole introduction rule. Baseline analysis failure makes affected classification unknown and blocks strict differential enforcement.

### Make analyzer coverage explicit

The authoritative strict PR-range profile is the schema-versioned `pr-range-v1` definition in `run/runner.py`, serialized into the report and bound by the trusted policy/config digest. Its closed membership is:

| Analyzer ID | Status |
|---|---|
| `ruff` | required |
| `radon` | required |
| `semgrep` | required |
| `semgrep-bugs` | required when the trusted target-base-tip policy snapshot contains the governed bugs configuration; otherwise NOT_APPLICABLE, never skipped |
| `ai-bloat-ast` | required |
| `ast-clean-code` | required |
| `basedpyright` | required |
| `pylint` | required |
| `contracts` | required |
| `targeted-pytest-coverage` | conditionally required when the complete range contains governed production Python; otherwise NOT_APPLICABLE |

There are no optional analyzers in `pr-range-v1`. Future profile membership changes require a new profile ID/version and policy digest; an ad hoc extra analyzer may be advisory but cannot silently change this profile or assurance. The report lists every profile member with required/conditional status, per-snapshot ran/failed/NOT_APPLICABLE outcome, version, toolchain/configuration digest, duration, and diagnostic. For each member and snapshot, the planner derives eligible inputs from the immutable manifest. A structurally empty side records NOT_APPLICABLE with snapshot identity, input class, empty input set, manifest digest, and `absence_reason=no_eligible_inputs_in_snapshot`; if eligible input exists, missing/skipped/failed/timed-out/unparsable/identity-mismatched execution is `UNKNOWN`. The whole range remains applicable when either side contains governed Python. This explicit rule replaces adapter-specific empty-file early returns and covers add-only and delete-only ranges. A successful run with zero findings is still recorded as ran; it is not inferred from an empty finding list. `targeted-pytest-coverage` records the exact test paths/selectors, pytest/coverage versions, environment/config digest, per-snapshot outcome, and coverage artifact digest. Each snapshot containing selected governed production input requires a valid run. The merge-base side also may be NOT_APPLICABLE when immutable range evidence proves every required selector was introduced after the merge base; that record binds the absent paths/selectors and `absence_reason=not_present_at_merge_base`. Neither exception can excuse missing head tests while governed production input remains. Unexpected no-tests-collected, unavailable pytest, timeout, collection/internal/usage error, or missing/unreadable coverage is `UNKNOWN`; a collected head assertion failure is `FAIL`; a collected passing run records ran/pass plus its coverage findings. Range cannot use `--no-tests`.

Analyzer adapters SHALL surface timeout/unavailable/parse and documented tool/process-exit failures explicitly. In particular, the required `contracts` member includes its CrossHair subprocess and SHALL expose a timeout or process-error exit such as code 2 as failed coverage with diagnostics rather than an empty successful result; parsed counterexamples remain findings.

### Separate finding concepts

Finding fields distinguish:

- `severity`: impact if valid;
- `status`: open, fixed, or waived-by-reference;
- `differential_state`: introduced, fixed, unchanged, or unknown;
- `autofix_available`: whether a remediation mechanism exists;
- `blocking`: derived by the resolved policy.

An open fixable error remains unresolved and can block. A waiver is a signed governance overlay, not a detector outcome.

### Calibrate and version the terminal status

Schema `1.6` adds authoritative `assurance_status: PASS | FAIL | UNKNOWN | NOT_APPLICABLE`. A report cannot say all validations passed when a mandatory scope/analyzer/claim is unknown or skipped. Facts, deterministic claims, heuristic signals, and optional AI hypotheses remain labelled separately; an unvalidated hypothesis cannot block.

For one compatibility release, `overall_verdict` remains a non-authoritative legacy projection: PASS maps to PASS or PASS_WITH_ADVISORY, FAIL maps to FAIL, UNKNOWN maps conservatively to FAIL, and NOT_APPLICABLE maps to PASS_WITH_ADVISORY plus explicit no-impact text. Non-shadow exits for those statuses are respectively 0, 1, 1, and 0; shadow always exits 0 while preserving the authoritative status.

Legacy `enforcement_mode` is the normalized policy request, not a scope label: `enforce` becomes `full`; `full`, `changed`, and `shadow` remain those values. `changed` is restricted to the one-release changed/worktree compatibility path. The parser represents an omitted enforcement option distinctly from an explicit value: omitted plus range normalizes to strict `full`, while omitted plus the deprecated changed/worktree path retains `changed`. Explicit range plus changed-mode is invalid; strict range writes `full`, shadow range writes `shadow`, and range identity lives only in `scope_evidence`.

### Keep repository guidance on the same assurance boundary

Canonical merge/PR-quality instructions in both agent-rule files, the module and bundle guides, the generated `--instructions` text, the rules updater, bundled skill, and tracked generated skill copies SHALL use the executable complete-range form with full base/head identities and strict/full enforcement. They SHALL NOT recommend changed/worktree or positional branch-delta files as merge assurance.

The local pre-commit helper remains a staged positional-file gate and simplification preview remains a worktree workflow; both are useful but SHALL be labelled `explicit_files` or `worktree` and SHALL NOT satisfy `pr_range`. `AGENTS.md` already loads the canonical agent-rule files and need not duplicate the command. Tracked skill copies are regenerated from the bundled source through the existing updater, not hand-edited independently.

### Publish a closed consumer compatibility contract

The signed Code Review package SHALL include exactly `packages/specfact-code-review/src/specfact_code_review/resources/contracts/review-report-schema-1.6-consumer-matrix.json`. This checked-in machine-readable artifact binds schema 1.6's four authoritative statuses to valid legacy projections and strict/shadow exit behavior. It contains canonical minimal reports for PASS, FAIL, UNKNOWN, and NOT_APPLICABLE, required fields, permitted `overall_verdict` values, expected `ci_exit_code`, and mismatch-invalid cases. Tests and the package manifest bind its digest.

Core's existing `scripts/pre_commit_code_review.py` remains a staged `explicit_files` helper and SHALL NOT satisfy `pr_range`. In the separate core adoption PR it must stop deriving success solely from error findings and consume schema 1.6 `assurance_status`/`ci_exit_code` for its explicit-files report while preserving legacy fields. A separate PR-range consumer verifies scope and trusted target context. Task 4.7 is blocked until both consumers pass the exact signed compatibility matrix; a consumer that ignores or cannot parse authoritative status is rejected rather than falling back to legacy severity logic.

### Preserve assurance truth in the first-party ledger

For schema 1.6 reports, the ledger reads authoritative `assurance_status`, not the legacy `overall_verdict` projection. Persisted `LedgerRun.verdict`, `LedgerState.last_verdict`, local JSON, and Supabase constraints SHALL accept PASS, FAIL, UNKNOWN, and NOT_APPLICABLE while retaining PASS_WITH_ADVISORY only for reports older than 1.6.

PASS advances the pass streak and applies the existing reward rules. FAIL advances the block streak and applies the existing penalty rules. UNKNOWN and NOT_APPLICABLE are neutral audit events: retain the run, score, source reward metadata, findings, authoritative status, and the complete canonical schema 1.6 `report_json` plus SHA-256 `report_digest`; apply zero coins; set the applied last delta to zero; and leave both streak counters unchanged. They SHALL never trigger a pass bonus. Local JSON and Supabase `review_runs` persist the same report payload/digest so scope and analyzer diagnostics survive even when no finding exists. The DDL migration adds nullable report columns for legacy rows and remains backward compatible with existing three-value ledger records. Legacy reports older than 1.6 can yield only PASS or FAIL. Missing/invalid `assurance_status` in 1.6+ is invalid/unknown, never legacy fallback. Every post-analysis enrichment or model-copy path, including cleanup forecast refresh and `--requirements-evidence` context attachment in `run/commands.py`, SHALL preserve the input report's schema version, authoritative assurance status, scope evidence, analyzer coverage, and legacy projection; enrichment may add its own evidence but cannot downgrade or recompute assurance. Requirements attachment SHALL add only the validated requirements context to the existing schema 1.6 report and SHALL NOT hard-code an older schema version.

## Implementation Boundary

The normative closed path allowlist is the one enumerated in `tasks.md`; no implementation path outside that list is permitted without first updating this OpenSpec change and adding a named failing test. Exactly four new source/test files are permitted:

- `packages/specfact-code-review/src/specfact_code_review/run/scope.py`;
- `tests/unit/specfact_code_review/run/test_scope.py`;
- `packages/specfact-code-review/src/specfact_code_review/run/differential.py`;
- `tests/unit/specfact_code_review/run/test_differential.py`.

All other allowed work edits existing command, runner, report, named test/CLI-contract, documentation, and release-metadata seams listed in `tasks.md`. Git scope discovery and index/range materialization are confined to `scope.py`. Detector rules, analyzer implementations, AI review, Requirements-verdict fusion, pytest dependency inference, and unrelated bundles remain prohibited.

## Rollout and Rollback

1. Add red tests for scope truth, differential classification, analyzer coverage, and lifecycle semantics.
2. Add schema 1.6 scope/report fields and the closed legacy projection while dual-writing old fields for one compatibility release.
3. Publish only after command references, module metadata, registry artifacts, checksums, and signatures are regenerated by the canonical workflow; set the consuming core floor to `>=0.56.0,<1.0.0`.
4. Migrate core CI to explicit range scope in shadow mode and require `assurance_kind=pr_range`.
5. Compare against the #665–#671 adjudicated benchmark.
6. Enable strict unknown handling, then remove the deprecated alias in a later major-compatible release.
7. Roll back by restoring legacy command routing while retaining schema 1.6 evidence fields for diagnosis.

