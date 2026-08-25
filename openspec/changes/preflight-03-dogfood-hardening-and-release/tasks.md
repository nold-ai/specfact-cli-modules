# Tasks: preflight-03-dogfood-hardening-and-release (modules hardening/publication)

All tasks below are future implementation and release work. This planning change completes none of them and creates no `TDD_EVIDENCE.md`.

## 1. Dedicated session, worktree, and readiness

- [ ] 1.1 In a dedicated issue-linked session, create `feature/preflight-03-dogfood-hardening-and-release` from current `origin/dev` in a new modules worktree before any implementation edit.
- [ ] 1.2 Refresh hierarchy metadata and verify issue parent, labels, project `Todo`, assignee, blockers, and concurrency status; stop if the issue is already active elsewhere.
- [ ] 1.3 Verify modules `preflight-02` is merged and the paired core dogfood change records a go decision with exact evidence identities.

## 2. Evidence ledger, specs, and failing-first tests

- [ ] 2.1 Build the hardening ledger mapping every accepted item to dogfood evidence, contract path, generalized rule, regression selector, and owner; exclude unsupported ideas.
- [ ] 2.2 Finalize spec deltas for only those evidence-backed items and the stable release contract.
- [ ] 2.3 Add or update tests for the C14 corpus and bounded independent cases, then run them before production edits and record the failing results in a newly created `TDD_EVIDENCE.md`.

## 3. Minimal hardening implementation

- [ ] 3.1 Implement only fixes required by the approved failing regression cases.
- [ ] 3.2 Rerun the complete preflight loop after each contract-affecting fix and stop for a core follow-up if shared semantics must change.
- [ ] 3.3 Finalize the canonical module-owned workflow asset and supported CLI delegation without external adapter packages.

## 4. Stable release preparation and proof

- [ ] 4.1 Select the semver bump, exact supported core identity, and immutable compatibility matrix based on current release state.
- [ ] 4.2 Update the package manifest, registry metadata, generated references, and signed payload as one release surface through repository tooling.
- [ ] 4.3 Run fresh official install/discovery/load, contract, CLI, renderer, persistence, workflow, C14 corpus, and compatibility smokes.
- [ ] 4.4 Run format, type, lint, YAML, bundle-import, signature/version-bump, contract, smart-test, test, and SpecFact code-review gates; resolve every finding.
- [ ] 4.5 Run `openspec status --change preflight-03-dogfood-hardening-and-release --json` and `openspec validate preflight-03-dogfood-hardening-and-release --strict` and record observed evidence.

## 5. Publication, delivery, and cleanup

- [ ] 5.1 Publish only through the official signed module release flow and verify immutable artifact, registry, checksum, signature, and core-compatibility identities.
- [ ] 5.2 Update downstream issues with the exact stable handoff and unblock them only after readback succeeds.
- [ ] 5.3 Open the implementation/release PR to `dev` as the final pre-merge task, linking the paired core evidence and issue.
- [ ] 5.4 After merge/publication, run `openspec archive preflight-03-dogfood-hardening-and-release`, update ordering/source mirrors, and remove the dedicated worktree and merged branch.
