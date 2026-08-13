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
- `--scope index`: staged/index changes relative to HEAD;
- `--scope range --base-ref <full-ref> --head-ref <full-ref>`: committed merge-base-to-head delta;
- `--scope full`: all eligible repository files;
- positional files: one explicit caller-selected set.

`--scope changed` remains one-release deprecated compatibility for `worktree` and prints a warning. CI/enforce mode rejects an implicit or ambiguous changed scope when PR/range semantics are required.

Range resolution records full base, head, and merge-base SHAs; diff/path digest; selected file and line facts; rename/deletion facts; filters/facets; repository root; command request; resolver version; and diagnostics. Tests are included by default. Explicit facet exclusion is recorded and cannot be mistaken for analyzed evidence.

### Empty and unresolved are different

A successfully resolved range with zero governed Python files is `NOT_APPLICABLE`. A missing ref, shallow history, Git error, timeout, repository mismatch, or parsing failure is `UNKNOWN`. Enforce mode exits non-zero for unknown; shadow may exit zero but must preserve the unknown report/status.

### Use symmetric base/head analysis

Range review evaluates both snapshots with the same analyzer version, configuration digest, policy, and normalization. Stable fingerprints use analyzer/rule, semantic file anchor, symbol/region identity, and normalized message fields. Exact implementation may vary by tool but line-number equality alone is insufficient.

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

### Calibrate the terminal status

Review assurance status is `PASS`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE`. A report cannot say all validations passed when a mandatory scope/analyzer/claim is unknown or skipped. Facts, deterministic claims, heuristic signals, and optional AI hypotheses remain labelled separately; an unvalidated hypothesis cannot block.

## Implementation Boundary

The future behavior PR may touch only the Code Review command/resolver/runner/report models, focused fixtures/tests, CLI contracts, docs, and release metadata. It must not edit analyzer rule packs or unrelated bundles.

## Rollout and Rollback

1. Add red tests for scope truth, differential classification, analyzer coverage, and lifecycle semantics.
2. Add new scope/report fields while dual-writing legacy fields.
3. Migrate core CI to explicit range scope in shadow mode.
4. Compare against the #665–#671 adjudicated benchmark.
5. Enable strict unknown handling, then remove the deprecated alias in a later major-compatible release.
6. Roll back by restoring legacy command routing while retaining new evidence fields for diagnosis.

