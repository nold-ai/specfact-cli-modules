# Tasks: Requirement Scenario Runtime Proof

## TDD / SDD order (enforced)

Specs first, then scenario-mapped tests and captured failing evidence, then
production code. Do not implement planning, reconciliation, or review-context
behavior before its tests exist and have failed for the expected reason.

---

## 1. Worktree and readiness

- [x] 1.1 Create issue-linked worktree
  `../specfact-cli-modules-worktrees/feature/requirements-07-scenario-runtime-proof`
  from current `origin/dev`; verify branch and clean scope.
- [x] 1.2 Create modules User Story #368; verify labels, project `Todo`, parent
  Feature #161, Epic #144, and native blocking relation to core #662.
- [ ] 1.3 Before implementation, recheck that #368 is not already `In Progress`
  elsewhere and verify the paired core proposal remains contract-compatible.

## 2. Specification and failing evidence

- [ ] 2.1 Refine the scenario-proof and review-context specs only if current
  release reality exposes a concrete ambiguity; mirror any paired contract
  adjustment in core before implementation.
- [ ] 2.2 Add failing Requirements tests for stable scenario IDs, touchpoint
  validation, canonical plan IDs, exact pytest selectors, unsafe-selector
  rejection, and deterministic plan ordering.
- [ ] 2.3 Add failing reconciliation tests for passed, failed, skipped,
  uncollected, duplicate, stale, mismatched, missing-canonical-selector, and
  malformed JUnit cases.
- [ ] 2.4 Add failing Code Review tests for valid, absent, red, stale, and
  unsupported Requirements evidence context without verdict substitution.
- [ ] 2.5 Record commands, timestamps, and expected failures in
  `TDD_EVIDENCE.md` before production edits.

## 3. Module implementation

- [ ] 3.1 Add typed, contract-decorated scenario, touchpoint, selector, plan,
  reconciliation, and proof-state models to `specfact-requirements`.
- [ ] 3.2 Extend `specfact requirements evidence` with explicit plan and
  reconciliation inputs/outputs while preserving current staged/base-ref use.
- [ ] 3.3 Parse bounded JUnit XML defensively and bind exact results to the plan,
  source revisions, and result digest; do not invoke a test runner.
- [ ] 3.4 Add optional validated Requirements evidence context to
  `specfact code review run` and emit deterministic coverage findings without
  changing the Requirements verdict.
- [ ] 3.5 Keep output ordering, remediation, profile severity, and old-report
  compatibility deterministic across repeated runs.

## 4. Passing evidence and integration proof

- [ ] 4.1 Run focused Requirements and Code Review tests and record passing
  evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Add integration fixtures proving plan -> external pytest/JUnit ->
  reconciliation -> review-context handoff without module-owned execution.
- [ ] 4.3 Verify paired core #662 can consume only public released interfaces;
  publish compatibility fixtures and the immutable release commit.

## 5. Quality, documentation, and release

- [ ] 5.1 Run format, type-check, lint, YAML lint, bundle-import, contract,
  smart-test, and full focused test gates.
- [ ] 5.2 Run fresh changed/full SpecFact code review with `--bug-hunt`; resolve
  every finding at every severity and record the final report evidence.
- [ ] 5.3 Update Requirements and Code Review guides, command references, and
  modules.specfact.io navigation with proof semantics and limitations.
- [ ] 5.4 Bump affected bundle versions, regenerate registry artifacts and
  command overviews, sign changed module payloads, and verify signatures/version
  policy from the filesystem.
- [ ] 5.5 Run `openspec validate requirements-07-scenario-runtime-proof --strict`
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
