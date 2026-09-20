# Tasks: code-review-15-signal-calibrated-blocking-gate

## Scope rescope — 2026-09-20

Remove optional preflight hardening #432 as a prerequisite. Preserve C14 protected adoption, policy/profile and exception authority, measured calibration, meaningful dogfood checks and signatures. Use current-run results; historical RED and development seals are not required.

This owner-requested planning amendment supersedes conflicting development-workflow and dependency wording below. Runtime behavior is unchanged. Replacement policy: [core #740](https://github.com/nold-ai/specfact-cli/issues/740) and [modules #481](https://github.com/nold-ai/specfact-cli-modules/issues/481).

## 1. Worktree and readiness

- [x] 1.1 Create `feature/code-review-15-signal-calibrated-blocking-gate` from modules `dev` in the required sibling worktree.
- [ ] 1.2 Reverify existing issue [#417](https://github.com/nold-ai/specfact-cli-modules/issues/417), parent #163, labels, assignee, type, project status and current native blockers before implementation. The 2026-09-20 readback has four open prerequisites (modules #158/#167 and core #248/#680); closed modules #416 and core #237 remain historical baseline relationships. Optional #432 is not a prerequisite.
- [ ] 1.3 Revalidate the already-shipped C14 schema 1.6 signed producer and compatible release identity; verify the still-pending protected core adoption #680 is released. Closed modules #416 is historical, not unfinished work.
- [ ] 1.4 Verify policy-02 and governance-02 expose the signed policy and authenticated exception contracts consumed here.
- [ ] 1.5 If any readiness item is missing or in progress elsewhere, stop production implementation and retain planning/test design only.

## 2. Spec and compatibility freeze

- [x] 2.1 Add proposal, design, task plan, and delta specs for schema 1.7, verdict mapping, calibration, identity/dedup, and suppressions.
- [x] 2.2 Add the paired core C15 change #679 and planning cross-links in both `CHANGE_ORDER.md` files. This records planning only, not runtime adoption. C15 remains #417 -> #679; the separate MEB migration is #481 -> core #740.
- [ ] 2.3 Freeze the schema 1.7 producer/consumer matrix, signed calibration profile, and suppression grammar/resource digests.
- [x] 2.4 Update the internal wiki source page and rebuild the graph.
- [x] 2.5 Run `openspec validate code-review-15-signal-calibrated-blocking-gate --strict`.

## 3. Tests first

- [ ] 3.1 Add report/scorer tests for score-independent verdicts, info neutrality, fixable-error blocking, shadow truth, and UNKNOWN fail-closed behavior. Replace the legacy simplify-enforce regression with advisory safe-mechanical exit-zero/count-zero, effective-error and uncertainty blocking cases; retain guided output and safe-only rewrite coverage.
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
- [ ] 5.2 Before collecting activation-calibration observations, publish and review the bounded method in the public change: immutable corpus references, sampling frame/unit, strata/quotas and selection algorithm/seed, adjudication labels and disagreement handling, precision estimand/weights, and a statistically justified interval calculation. Resolve the proposed targets in the design; no frozen audit or valid weighted-Wilson construction is presently established.
- [ ] 5.3 Execute that reviewed method using existing review outputs and one adjudicated sample; activate blocking only if its finalized precision/confidence and minimum-sample criteria pass. Keep shadow while method or results are incomplete. Repeat calibration for relevant rule/policy changes, not ordinary PR delivery; do not add a per-PR proof ledger.
- [ ] 5.4 Keep shadow mode and recalibrate if the measurement target is missed.
- [ ] 5.5 Update bundle docs, bump the module minor version, regenerate/check signed resources, and verify exact core compatibility.
- [ ] 5.6 Run format, type-check, lint, yaml, signature, contract, smart/full tests, independent static analysis, and fresh SpecFact review evidence.
- [ ] 5.7 Release the signed module before the core adoption; do not archive until paired runtime evidence is complete.
