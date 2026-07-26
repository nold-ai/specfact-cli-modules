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

- [x] 4.1 Run targeted tests, strict OpenSpec validation, and required quality
  gates; record passing evidence.
- [x] 4.2 Run the changed-line SpecFact code review and resolve all findings.
- [x] 4.3 Open a PR to `dev` with the JSON evidence contract and its limits.

## 5. Production stability follow-up

- [x] 5.1 Replace invalid editable installation of the Requirements bundle with
  repository-local source-root bootstrap in the workflow.
- [x] 5.2 Write deterministic failed JSON and Markdown evidence fallback when
  setup fails before the adapter runs.
- [x] 5.3 Add workflow contract coverage for local source bootstrap and setup
  failure artifact retention; capture failing-before and passing-after evidence.
- [x] 5.4 Keep the shipped-source dogfood regression valid when OpenSpec moves
  completed changes into date-prefixed archive directories.
