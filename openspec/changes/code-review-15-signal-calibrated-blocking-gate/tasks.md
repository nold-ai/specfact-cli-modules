# Tasks: code-review-15-signal-calibrated-blocking-gate

## Scope rescope — 2026-09-20

Remove optional preflight hardening #432 as a prerequisite. Preserve C14 protected adoption, policy/profile and exception authority, measured calibration, meaningful dogfood checks and signatures. Use current-run results; historical RED and development seals are not required.

This owner-requested planning amendment supersedes conflicting development-workflow and dependency wording below. Runtime behavior is unchanged. Replacement policy: [core #740](https://github.com/nold-ai/specfact-cli/issues/740) and [modules #481](https://github.com/nold-ai/specfact-cli-modules/issues/481).

## 1. Worktree and readiness

- [x] 1.1 Create `feature/code-review-15-signal-calibrated-blocking-gate` from modules `dev` in the required sibling worktree.
- [x] 1.2 Create public issue [#417](https://github.com/nold-ai/specfact-cli-modules/issues/417) and verify parent #163, labels, assignee, User Story type, SpecFact CLI/Todo project metadata, and all five native blocked-by relationships from live GitHub.
- [ ] 1.3 Verify C14 and its paired protected core adoption are released with the signed schema 1.6 identity.
- [ ] 1.4 Verify policy-02 and governance-02 expose the signed policy and authenticated exception contracts consumed here.
- [ ] 1.5 If any readiness item is missing or in progress elsewhere, stop production implementation and retain planning/test design only.

## 2. Spec and compatibility freeze

- [x] 2.1 Add proposal, design, task plan, and delta specs for schema 1.7, verdict mapping, calibration, identity/dedup, and suppressions.
- [x] 2.2 Add the paired core change and cross-link both `CHANGE_ORDER.md` files.
- [ ] 2.3 Freeze the schema 1.7 producer/consumer matrix, signed calibration profile, and suppression grammar/resource digests.
- [x] 2.4 Update the internal wiki source page and rebuild the graph.
- [x] 2.5 Run `openspec validate code-review-15-signal-calibrated-blocking-gate --strict`.

## 3. Tests first

- [ ] 3.1 Add report/scorer tests for score-independent verdicts, info neutrality, fixable-error blocking, shadow truth, and UNKNOWN fail-closed behavior.
- [ ] 3.2 Add D1 tests for opt-in scope and every excluded callable class.
- [ ] 3.3 Add D2 tests for override, ABC, Protocol, resolved base, unresolved base, and unconstrained functions.
- [ ] 3.4 Add D3 tests for symbol/span reconciliation, ambiguity, exact same-invocation coalescing, occurrence multiplicity, and cross-tool preservation.
- [ ] 3.5 Add D4 tests for thresholds, test/CLI/constrained contexts, Click/Typer aliases, Pylint grouping, and Semgrep mapping.
- [ ] 3.6 Add suppression tests for line/statement scope, missing reason, wildcard, mismatch, expiry, trusted-base approval, and candidate self-approval rejection.
- [ ] 3.7 Observe the focused regression failure before production edits and retain a brief validation summary; no committed output transcript is required.

## 4. Implementation

- [ ] 4.1 Implement schema 1.7 fields and deterministic aggregate/legacy projections without changing C14 scope/differential behavior.
- [ ] 4.2 Implement signed severity/context policy resolution and score-independent enforcement.
- [ ] 4.3 Implement D1 and D2 AST/hierarchy applicability.
- [ ] 4.4 Implement D3 attribution normalization and multiplicity-preserving presentation deduplication.
- [ ] 4.5 Implement D4 calibrated mappings and Ruff/Pylint corroboration grouping.
- [ ] 4.6 Implement directive parsing and governance-02 exception matching; preserve every suppression attempt in evidence.
- [ ] 4.7 Re-run focused tests and record passing evidence.

## 5. Dogfood, measurement, and delivery

- [ ] 5.1 Run full shadow reviews on modules and core; classify and remediate every effective error or add an approved time-bound exception.
- [ ] 5.2 Repeat the frozen 40-PR replay and n=150 stratified adjudication with seed 20260819, including at least 30 human-reviewed error cases.
- [ ] 5.3 Require weighted error precision >=80%, Wilson 95% lower bound >=70%, and at least 40 adjudicated errors before blocking activation.
- [ ] 5.4 Keep shadow mode and recalibrate if the measurement target is missed.
- [ ] 5.5 Update bundle docs, bump the module minor version, regenerate/check signed resources, and verify exact core compatibility.
- [ ] 5.6 Run format, type-check, lint, yaml, signature, contract, smart/full tests, independent static analysis, and fresh SpecFact review evidence.
- [ ] 5.7 Release the signed module before the core adoption; do not archive until paired runtime evidence is complete.
