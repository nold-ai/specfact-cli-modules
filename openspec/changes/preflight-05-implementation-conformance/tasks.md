# Tasks: preflight-05-implementation-conformance (modules runtime)

All tasks below are future implementation work. This planning change completes none of them and creates no generated evidence or `TDD_EVIDENCE.md`.

## 1. Dedicated session, worktree, and readiness

- [ ] 1.1 In a dedicated issue-linked session, create `feature/preflight-05-implementation-conformance` from current `origin/dev` in a new modules worktree before any implementation edit.
- [ ] 1.2 Refresh hierarchy metadata and verify issue type, parent, labels, project `Todo`, assignee, blockers, and concurrency status.
- [ ] 1.3 Verify the exact stable preflight module and released paired core conformance interface identities.

## 2. Specification and failing-first evidence

- [ ] 2.1 Finalize command, evidence adapter, validator, rendering, persistence, and workflow deltas without adding preflight MVP or external adapter scope.
- [ ] 2.2 Add tests mapped to every invalid-seal, stale-evidence, drift, reapproval, renderer-parity, persistence, and opt-in-policy scenario.
- [ ] 2.3 Run targeted tests before production edits and record failing-first results in a newly created `TDD_EVIDENCE.md`.

## 3. Minimal runtime implementation

- [ ] 3.1 Implement `specfact preflight conform <change-id>` against the released core interface.
- [ ] 3.2 Implement evidence import/extraction adapters and closed mapping validators without duplicating existing analyzers.
- [ ] 3.3 Implement human/JSON rendering, explicit drift resolution handoff, and optional atomic persistence.
- [ ] 3.4 Keep delivery enforcement opt-in and exclude external harness packages.

## 4. Passing evidence and quality gates

- [ ] 4.1 Re-run mapped tests and capture passing evidence after implementation.
- [ ] 4.2 Run format, type, lint, YAML, bundle-import, signature/version, contract, smart-test, test, and SpecFact code-review gates; resolve all findings.
- [ ] 4.3 Run official install/load and compatibility smoke against the selected released core/module identities.
- [ ] 4.4 Run `openspec status --change preflight-05-implementation-conformance --json` and `openspec validate preflight-05-implementation-conformance --strict`.

## 5. Delivery and post-merge cleanup

- [ ] 5.1 Document assurance limits, opt-in policy, and rollback using observed evidence only.
- [ ] 5.2 Open the implementation PR to `dev` as the final pre-merge task, linking the paired core issue and evidence.
- [ ] 5.3 After merge, run `openspec archive preflight-05-implementation-conformance`, update ordering/source mirrors, and remove the dedicated worktree and merged branch.
