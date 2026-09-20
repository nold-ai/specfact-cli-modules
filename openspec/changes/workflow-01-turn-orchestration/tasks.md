## 1. Worktree and live readiness

- [ ] 1.1 Create a dedicated `codex/workflow-01-turn-orchestration` worktree from current `origin/dev`; bootstrap its environment serially.
- [ ] 1.2 Refresh native issue type/parent/assignee/labels/project/status/blockers and reverse edges; coordinate ownership and verify the modules #481 contract handoff before integrating it.
- [ ] 1.3 Revalidate strict OpenSpec and current module/core registry interfaces. Use effective governance or an explicit owner-authorized exception; do not infer R09 runtime completion from this plan.

## 2. Spec-derived failures

- [ ] 2.1 Add deterministic fixture tests for missing tools, index/worktree/range selection, independent failed gates, schema mismatch and affected-gate recheck.
- [ ] 2.2 Add identity/state tests for dirty and untracked content, configuration/module changes, concurrent edits, unique runs, atomic persistence, controller locks and fresh-session verification.
- [ ] 2.3 Add mocked PR tests for pending CI, unresolved reviews, changed remote heads, unauthorized writes, untrusted review text, subprocess timeout, no progress, oscillation and lost effect acknowledgements.
- [ ] 2.4 Observe meaningful failing cases before corresponding implementation and record evidence under effective governance; retain TDD_EVIDENCE.md if still required, without a new mandatory history protocol.

## 3. Deterministic module slice

- [ ] 3.1 Add the package/manifest and command registration using existing core APIs and icontract/beartype on public surfaces; keep core compatibility explicit.
- [ ] 3.2 Implement producer adapters, exact snapshots and independent outcomes; consume the released R09 contract without adding I/O to Requirements.
- [ ] 3.3 Implement pre-validation observations and standalone check-only verify with complete required-gate diagnostics and semantic result projections.
- [ ] 3.4 Implement atomic local state, identities, lock/resume and affected-input invalidation; demonstrate no source/index mutation and no history prerequisite.
- [ ] 3.5 Open a bounded implementation PR for the deterministic slice with actual tests/gates before any release or trusted adoption.

## 4. Bounded local and PR loops

- [ ] 4.1 Implement implement/fix planning and checkpoints with three-iteration budgets, timeouts, progress detection and recheck of all affected gates.
- [ ] 4.2 Implement read-only PR observation against exact heads and independent check/review state; classify pending and infrastructure outcomes.
- [ ] 4.3 Implement explicit apply/publish/thread-write capabilities, stable operation keys and restart reconciliation; test the five-round/time budgets and external-head stops before a live opt-in pilot.
- [ ] 4.4 Package prefixed reusable skills and validate all documented command examples against the installed CLI; repository wrappers remain owned by core.

## 5. Quality, integration and signed handoff

- [ ] 5.1 Run applicable lint/type, contract, smart/full tests, independent security, review, prompt-command, import-boundary and strict OpenSpec gates; resolve findings using their effective owning policy.
- [ ] 5.2 Document commands, capability opt-ins, offline behavior, state recovery, compatibility and rollback; update actual module docs navigation/permalinks and core cross-links.
- [ ] 5.3 Prepare manifest/registry/version/changelog and signing compatibility tests for the added package; verify payload/version integrity and signatures under the existing release policy.
- [ ] 5.4 Open/update final implementation PRs to dev with current validation; integrate through normal review before canonical signed publication. Do not wait until publication to create the first PR.
- [ ] 5.5 After reviewed integration, publish through the canonical release tooling, verify immutable artifact/signature/core compatibility and provide the exact handoff to core #742; rehearse rollback without erasing producer outputs.
- [ ] 5.6 Reconcile issue/source/wiki status after delivery; archive completed implementation natively and clean worktrees after merge. Keep this proposal and its implementation tasks uncompleted now.

Implementation is unstarted. Split an observed task exceeding two hours into bounded sessions, retaining spec/test-before-code order in every slice. The producer release never waits for core adoption of that same release.
