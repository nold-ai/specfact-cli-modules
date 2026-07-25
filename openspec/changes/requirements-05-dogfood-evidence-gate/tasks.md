# Tasks: requirements-05-dogfood-evidence-gate

## 1. Readiness and scope

- [x] 1.1 Create issue #352 with parent feature #161, labels, assignee, and
  project-board assignment.
- [x] 1.2 Create `feature/requirements-05-dogfood-evidence-gate` from
  `origin/dev` in a dedicated worktree.
- [x] 1.3 Refresh the GitHub hierarchy cache and verify issue metadata.

## 2. Specification and failing evidence

- [x] 2.1 Add the OpenSpec delta for requirements-evidence orchestration.
- [x] 2.2 Add unit tests for green, red, and skipped verdicts plus source
  discovery.
- [x] 2.3 Run the new tests before production edits and record the expected
  failing evidence in `TDD_EVIDENCE.md`.

## 3. Implementation

- [x] 3.1 Implement the deterministic adapter, evidence-sidecar overlay, and JSON envelope.
- [x] 3.2 Add the GitHub Actions job, summary, and always-uploaded artifact.
- [x] 3.3 Add user-facing documentation that distinguishes evidence validity
  from executed-test proof.

## 4. Verification and delivery

- [ ] 4.1 Run targeted tests, strict OpenSpec validation, and required quality
  gates; record passing evidence.
- [ ] 4.2 Run the changed-line SpecFact code review and resolve all findings.
- [ ] 4.3 Open a PR to `dev` with the JSON evidence contract and its limits.
