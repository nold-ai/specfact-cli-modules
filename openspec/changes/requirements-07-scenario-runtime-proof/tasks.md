# Tasks: Requirement Scenario Runtime Proof

## TDD / SDD order (enforced)

Specs first, then scenario-mapped tests and captured failing evidence, then
production code. Do not implement planning or reconciliation behavior before
its tests exist and have failed for the expected reason.

---

## 1. Worktree and readiness

- [x] 1.1 Create issue-linked worktree
  `../specfact-cli-modules-worktrees/feature/requirements-07-scenario-runtime-proof`
  from current `origin/dev`; verify branch and clean scope.
- [x] 1.2 Create modules User Story #368; verify labels, project `Todo`, parent
  Feature #161, Epic #144, and native blocking relation to core #662.
- [x] 1.3 Recheck #368 ownership and verify the paired core proposal remains
  contract-compatible. On 2026-08-04, #368 was confirmed as the active
  `In Progress` item for this linked PR; the paired core #662 proposal/design
  require finalized schema-v2 proof, independent review provenance, and no
  verdict fusion. The shipped `nold-ai/specfact-cli` generated command
  references do not yet expose `--requirements-evidence`; this is an explicit
  release boundary, not a completed cross-repository publication. Core #662
  remains blocked until this module version is published and core regenerates
  its references from the released module metadata. This public context input
  supplies the required contract without claiming the paired release is done.

## 2. Specification and failing evidence

- [x] 2.1 Refine the scenario-proof specs when current release reality exposes
  a concrete ambiguity. On 2026-08-05, the Code Review consumer contract was
  made explicit: a passing final proof retains a valid `red-junit` or
  digest-bound `legacy-tdd-ledger` basis before it can be attached as review
  provenance.
- [x] 2.2 Add failing Requirements tests for schema-v2 proposal mappings,
  rationale/touchpoint/verification-case completeness, mapping digest,
  digest-bound acceptance, and explicit not-yet-available execution state.
- [x] 2.3 Add failing tests for exact pytest selectors, unsafe-selector
  rejection, deterministic plan ordering, and reconciliation for passed, failed, skipped,
  uncollected, duplicate, stale, mismatched, missing-canonical-selector, and
  malformed JUnit cases.
- [x] 2.4 Record commands, timestamps, and expected failures in
  `TDD_EVIDENCE.md` before production edits.

## 3. Module implementation

- [x] 3.1 Add typed, contract-decorated lifecycle mapping, acceptance,
  touchpoint, selector, plan, reconciliation, and proof-state models to
  `specfact-requirements`.
- [x] 3.2 Extend `specfact requirements evidence` with required-maturity,
  review-evidence, and plan-output inputs while preserving the legacy
  staged/base-ref contract; add `specfact requirements reconcile` without
  module-owned test execution.
- [x] 3.3 Parse bounded JUnit XML defensively and bind exact results to the plan,
  source revisions, and result digest; do not invoke a test runner.
- [x] 3.4 Keep output ordering, remediation, profile severity, and old-report
  compatibility deterministic across repeated runs.
- [x] 3.5 Add a Code Review public context input that accepts only finalized
  Requirements proof, preserves independent provenance in the review report,
  and never fuses verdicts.

## 4. Passing evidence and integration proof

- [ ] 4.1 Run focused Requirements tests and record passing
  evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Add integration fixtures proving plan -> external pytest/JUnit ->
  reconciliation without module-owned execution.
- [ ] 4.3 Verify paired core #662 can consume only public released interfaces;
  publish compatibility fixtures and the immutable release commit.

## 5. Quality, documentation, and release

- [ ] 5.1 Run format, type-check, lint, YAML lint, bundle-import, contract,
  smart-test, and full focused test gates.
- [ ] 5.2 Run fresh changed/full SpecFact code review with `--bug-hunt`; resolve
  every finding at every severity and record the final report evidence.
- [ ] 5.3 Update Requirements guides, command references, and
  modules.specfact.io navigation with proof semantics and limitations.
- [x] 5.4 Bump affected bundle versions, regenerate registry artifacts and
  command overviews, sign changed module payloads, and verify signatures/version
  policy from the filesystem.
- [x] 5.5 Run `openspec validate requirements-07-scenario-runtime-proof --strict`
  and retain the validation result.

## 6. Delivery

- [ ] 6.1 Commit implementation, push the issue-linked feature branch, and open
  the implementation PR to `dev` using the repository PR template and
  `Fixes nold-ai/specfact-cli-modules#368`.
- [ ] 6.2 Add the PR to project 1, set implementation status to `In Progress`,
  verify Development/parent/blocker metadata, and publish the immutable release
  handoff for core #662.
- [ ] 6.3 After merge and core handoff, archive only with
  `openspec archive requirements-07-scenario-runtime-proof` from repo root.

## Post-merge cleanup

- [ ] Return to the primary modules checkout, fetch `dev`, remove the worktree,
  delete the local feature branch after merge, prune worktrees, and optionally
  delete the merged remote branch.
