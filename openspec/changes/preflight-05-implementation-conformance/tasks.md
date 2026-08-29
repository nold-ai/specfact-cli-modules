# Tasks: preflight-05-implementation-conformance (modules runtime)

All tasks below are future implementation work. This planning change completes none of them and creates no generated evidence or `TDD_EVIDENCE.md`.

## 1. Dedicated session, worktree, and readiness

- [ ] 1.1 In a dedicated issue-linked session, create `feature/preflight-05-implementation-conformance` from current `origin/dev` in a new modules worktree before any implementation edit.
- [ ] 1.2 Refresh hierarchy metadata and verify #434 is `Todo`, correctly parented/labeled/assigned, blocked only by stable modules #432 and core #684, blocks core #251, and is not concurrently `In Progress`.
- [ ] 1.3 Read back the exact released preflight, Requirements, C14 scope/capsule, code-review JSON, and core #684 identities; preserve C14 #416 state unless separately authorized.

## 2. Specification and failing-first evidence

- [ ] 2.1 Finalize checkpoint/conform CLI, profile, evidence adapter, cache, pre-commit, remediation packet, bounded workflow, persistence, signing, and publication deltas without external adapter packaging.
- [ ] 2.2 Add mapped tests for seal selection, worktree/index/range identity, complete Git transitions, scope/component/risk mapping, Requirements selectors/JUnit, code-review import, cache invalidation, statuses/authority, profile behavior, renderer parity, persistence, and publication.
- [ ] 2.3 Add workflow tests for deterministic packets, three-cycle maximum, repeated fingerprints, scope expansion, unknown/design stops, and non-mutation of sealed artifacts.
- [ ] 2.4 Run targeted tests before production edits and record failing-first results in a new `TDD_EVIDENCE.md`.

## 3. Minimal runtime implementation

- [ ] 3.1 Implement `specfact preflight checkpoint <change-id> --scope worktree|index --profile slice|commit|deep` against released core #684 interfaces.
- [ ] 3.2 Reuse C14 scope/capsule/toolchain extraction, Requirements plans/selectors/JUnit, and code-review JSON; add no duplicate selector or analyzer schema.
- [ ] 3.3 Implement obligation selection, pytest execution, status aggregation, digest-bound caching, human/JSON rendering, compact remediation packets, and optional atomic persistence.
- [ ] 3.4 Implement the seal-aware index pre-commit wrapper and harness-neutral implementation-check workflow; keep the deterministic CLI LLM/network/write free.
- [ ] 3.5 Preserve `specfact preflight conform <change-id>` as explicit immutable-range evaluation with separate authority.

## 4. Dogfood and passing evidence

- [ ] 4.1 Run shadow dogfood against C14-derived fixtures for illegal analyzer exits, cache identity/mode drift, malformed input, deletion-only changes, quoted/trailing/Unicode paths, suppression relocation, and FAIL/UNKNOWN precedence; every accepted fixture must fail before simulated PR delivery.
- [ ] 4.2 Record duration, locally detected defects, cycles-to-green, packet size, repeated finding classes, false PASS, and later PR findings; enable seal-aware blocking only when the accepted corpus has zero false PASS and no destructive/ambiguous behavior.
- [ ] 4.3 Run format, type, lint, YAML, bundle-import, contract, smart-test, full test, independent analysis where applicable, and SpecFact code-review gates; resolve all findings.
- [ ] 4.4 Run strict OpenSpec and Requirements planning/evidence gates and record only observed results.

## 5. Release and downstream handoff

- [ ] 5.1 Version, sign, verify, compatibility-test, and publish one immutable module/workflow identity containing checkpoint and conform behavior.
- [ ] 5.2 Hand that exact identity to core #251/#253 and modules #433; do not create external adapter packages in this change.
- [ ] 5.3 Open the implementation PR to `dev` as the final pre-merge task, linking core #684, dogfood, assurance limits, metrics, and rollback evidence.
- [ ] 5.4 After merge, run `openspec archive preflight-05-implementation-conformance`, update ordering/source mirrors, and remove the dedicated worktree and merged branch.
