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

The trusted policy/config identity is resolved once from the merge-base policy epoch and applied to both range snapshots. Candidate analyzer-config changes remain visible in scope evidence but cannot authorize or weaken their own comparison; they run only as separately labelled shadow evidence until promoted.

Before and after each snapshot analysis, the resolver SHALL verify the selected-input manifest. A missing object, path escape, content mismatch, cleanup failure that prevents verification, or post-analysis mutation yields `UNKNOWN` with diagnostics. Index and range modes SHALL reject `--fix`, `--preview-fixes`, and `--with-mutation` before materialization. Those operations require a separate worktree/explicit-file run and cannot be attached to index-snapshot or PR-range assurance.

### Empty and unresolved are different

A successfully resolved range with zero governed Python files is `NOT_APPLICABLE`. A missing ref, shallow history, Git error, timeout, repository mismatch, or parsing failure is `UNKNOWN`. Enforce mode exits non-zero for unknown; shadow may exit zero but must preserve the unknown report/status.

### Use symmetric merge-base/head analysis

Range review evaluates the resolved merge-base snapshot and head snapshot with the same analyzer version, configuration digest, policy, and normalization. The current base-ref tip participates only in merge-base resolution; target-branch commits after divergence are never treated as the PR baseline or classified as feature-branch fixes. Stable fingerprints use analyzer/rule, semantic file anchor, symbol/region identity, and normalized message fields. Exact implementation may vary by tool but line-number equality alone is insufficient.

Each head finding is classified `introduced`, `unchanged`, or `unknown`; missing head fingerprints matched at base are `fixed`. Changed lines are supporting evidence, never the sole introduction rule. Baseline analysis failure makes affected classification unknown and blocks strict differential enforcement.

### Make analyzer coverage explicit

The report lists every mandatory analyzer with required/ran/skipped/failed, version, configuration digest, duration, and diagnostic. Missing, skipped, failed, timed-out, or unparsable mandatory analysis yields `UNKNOWN`; optional analyzers are clearly labelled optional.

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

Legacy `enforcement_mode` is the normalized policy request, not a scope label: `enforce` becomes `full`; `full`, `changed`, and `shadow` remain those values. `changed` is restricted to the one-release changed/worktree compatibility path. Range plus changed-mode is invalid; strict range writes `full`, shadow range writes `shadow`, and range identity lives only in `scope_evidence`. Legacy reports older than 1.6 can yield only PASS or FAIL. Missing/invalid `assurance_status` in 1.6+ is invalid/unknown, never legacy fallback.

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

