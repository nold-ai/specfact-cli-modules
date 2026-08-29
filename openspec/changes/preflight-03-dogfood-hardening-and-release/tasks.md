# Tasks: preflight-03-dogfood-hardening-and-release (modules hardening/publication)

All tasks below are future implementation and release work. This planning change completes none of them and creates no `TDD_EVIDENCE.md`.

## 1. Dedicated session, worktree, and readiness

- [ ] 1.1 In a dedicated issue-linked session, create `feature/preflight-03-dogfood-hardening-and-release` from current `origin/dev` in a new modules worktree before any implementation edit.
- [ ] 1.2 Refresh hierarchy metadata and verify issue parent, labels, project `Todo`, assignee, blockers, and concurrency status; stop if the issue is already active elsewhere.
- [ ] 1.3 Verify the complete core #682 -> modules #431 -> core C14 #680 -> core #683 sequence, confirm the paired core dogfood go decision, preserve modules C14 #416 as open and `In Progress` unless separately authorized, and identify the exact released registry-withdrawal command/workflow plus core installer-rejection contract; stop for a separate core change if either interface is absent.

## 2. Evidence ledger, specs, and failing-first tests

- [ ] 2.1 Build the hardening ledger mapping every accepted item to dogfood evidence, contract path, generalized rule, regression selector, and owner; exclude unsupported ideas.
- [ ] 2.2 Finalize spec deltas for only those evidence-backed items and the stable release contract.
- [ ] 2.3 Add or update tests for the C14 corpus and bounded independent cases, then run them before production edits and record the failing results in a newly created `TDD_EVIDENCE.md`.

## 3. Minimal hardening implementation

- [ ] 3.1 Implement only fixes required by the approved failing regression cases.
- [ ] 3.2 Rerun the complete preflight loop after each contract-affecting fix and stop for a core follow-up if shared semantics must change.
- [ ] 3.3 Finalize the canonical module-owned workflow asset and supported CLI delegation without external adapter packages.

## 4. Stable release preparation and proof

- [ ] 4.1 Select the semver bump, bounded supported core range, immutable minimum-core identity, dependency-backed upper bound, and supported compatibility matrix based on current release state.
- [ ] 4.2 Update the package manifest, registry metadata, structured release-history entry, generated references, and signed payload as one release surface through repository tooling; derive the inclusive minimum from the first immutable released core containing accepted #682 contracts, prove it by official tag/full commit/full tree, derive the exclusive maximum from the required dependency graph, exercise the exact minimum plus selected current in-range cores across supported Python versions, and reject empty, exact-only, ordinary-equality, wildcard, below-minimum, at-or-above-cap, unbounded, or matrix-unproven values before signing.
- [ ] 4.3 Run fresh official install/discovery/load, contract, CLI, renderer, persistence, workflow, C14 corpus, compatibility, withdrawal/supersession, and known-bad installer-rejection smokes; verify the signed workflow digest/version and delegated CLI identity as one tuple and prove the declared persisted-state rollback outcome, including the no-prior-stable-baseline case.
- [ ] 4.4 Run format, type, lint, YAML, bundle-import, signature/version-bump, contract, smart-test, test, and SpecFact code-review gates; resolve every finding.
- [ ] 4.5 Run `openspec status --change preflight-03-dogfood-hardening-and-release --json` and `openspec validate preflight-03-dogfood-hardening-and-release --strict` and record observed evidence.

## 5. Publication, delivery, and cleanup

- [ ] 5.1 Open, review, and merge the behavior-ready implementation PR to `dev`, linking the paired core evidence and issue; feature-branch artifacts are not publishable release identities.
- [ ] 5.2 Allow only the canonical post-merge publish workflow to generate, sign, and propose registry/archive/checksum/signature/history artifacts; review and merge that publication PR only after immutable artifact, registry, checksum, signature, core-compatibility, signed workflow version/digest, delegated CLI identity, history, rollback-operation, installer-rejection, and persisted-state rollback identities pass. Verify that every post-publication correction or withdrawal uses a new patch version and retains the prior artifact, digest, signature, registry record, and release-history entry unchanged.
- [ ] 5.3 Update downstream issues with the exact merged stable handoff, including the signed workflow version/digest and delegated CLI identity. Publication-PR merge and registry/install readback may unblock core #684 and C15. Modules #434 remains blocked until both this #432 handoff and core #684 are complete; #251, #253, and #433 remain downstream of signed #434 and never block it.
- [ ] 5.4 After implementation merge and verified publication, run `openspec archive preflight-03-dogfood-hardening-and-release`, update ordering/source mirrors, and remove the dedicated worktree and merged branch.
