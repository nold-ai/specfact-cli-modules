# Implementation tasks

Planning only. Implementation has not started. Brief validation notes and CI artifacts replace hosted RED checkpoints and committed transcripts.

## 1. Readiness

- [ ] 1.1 Create a fresh issue-linked worktree from current dev; verify #481 hierarchy, ownership and paired #740 scope.
- [ ] 1.2 Revalidate current schema/reconciliation and shipped core interfaces; supersede R07 without reopening #368 or R08.
- [ ] 1.3 Define the supported v3/v2 migration and signed release handoff without a circular core dependency.

## 2. Tests before code

- [ ] 2.1 Add focused cases for current passing results without RED; missing, malformed, empty, duplicate, failed, errored or skipped selected outcomes; observe the relevant failures before code changes.
- [ ] 2.2 Add cases for optional mapping and unassessed coverage, explicit legacy semantics, malformed-v3 rejection and independent Code Review verdicts.
- [ ] 2.3 Retain parser/resource bounds and ensure local report inputs cannot manufacture protected CI authority.

## 3. Implementation

- [ ] 3.1 Implement current as the default reconciliation stage using supplied current plan and JUnit; do not run Git, tests or network operations.
- [ ] 3.2 Finalize schema v3 independent current/chronology claims; preserve explicit v2 reading and stricter red/final callers.
- [ ] 3.3 Accept optional scenario mapping without claiming complete requirements coverage when absent.
- [ ] 3.4 Let Code Review consume current context without changing its independent verdict.
- [ ] 3.5 Update help/examples and affected module documentation, version compatibility and release metadata.

## 4. Verify and deliver

- [ ] 4.1 Run focused and applicable full tests, lint/type/contracts, independent review, strict OpenSpec validation and signing/publication checks; reference existing CI artifacts.
- [ ] 4.2 Verify the supported installed core/module combination and coordinate signed handoff to #740 through the canonical publication process.
- [ ] 4.3 Prepare the issue-linked implementation PR to dev with concise validation and rollback notes; push and open it.

After integration, publish through the canonical signed release process, reconcile superseded planning, archive completed changes with `openspec archive`, and remove the implementation worktree only after merge.
