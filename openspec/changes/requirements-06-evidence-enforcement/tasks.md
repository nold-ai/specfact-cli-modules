# Tasks: Reusable Requirements Evidence Command and Local Enforcement

## TDD / SDD order (enforced)

Specs first, then tests mapped to scenarios and failing evidence, then
production code. Do not implement command or hook behavior before failing tests
exist.

---

## 1. Worktree and readiness

- [x] 1.1 Create dedicated worktree
  `feature/requirements-06-evidence-enforcement` from `origin/dev` and verify
  it is not the protected checkout.
- [x] 1.2 Create or link the public GitHub issue after explicit user approval;
  verify parent, labels, project assignment, blockers, and concurrent work.
- [x] 1.3 Revalidate `requirements-05-dogfood-evidence-gate` implementation
  and archive status; preserve it as the evaluator-contract dependency rather
  than duplicating its behavior.

## 2. Spec-first and failing evidence

- [x] 2.1 Add the `requirements-evidence-command` spec delta and paired CLI
  integration design.
- [x] 2.2 Add command tests for base-ref mode, staged mode, mutually exclusive
  arguments, report-before-failure, skipped verdict, and stable JSON schema.
- [x] 2.3 Add index-snapshot tests proving unstaged OpenSpec and test-file
  edits cannot affect staged-mode validation.
- [x] 2.4 Add pre-commit and workflow contract tests for command invocation,
  always-retained artifacts, and agent-readable failure guidance.
- [x] 2.5 Run the new tests before production edits and record failing output
  in `TDD_EVIDENCE.md`.

## 3. Implementation

- [x] 3.1 Move evaluator orchestration into the Requirements runtime behind
  typed, contract-decorated public APIs; keep the current script as a thin
  compatibility wrapper until callers migrate.
- [x] 3.2 Add `specfact requirements evidence` with required output, optional
  Markdown summary, and exactly one of `--base-ref` or `--staged`.
- [x] 3.3 Materialize an isolated Git-index snapshot for staged mode, including
  repository-contained test targets referenced by evidence sidecars.
- [x] 3.4 Add a Requirements evidence stage before code review and contract
  tests in modules pre-commit Block 2; skip only when no active OpenSpec source
  is staged and print report/remediation paths on failure.
- [x] 3.5 Change the requirements-evidence CI workflow to invoke the module
  evaluator through its thin adapter while retaining the existing summary,
  artifact, and failure order; move invocation to the public command in the
  paired core CLI follow-up.
- [ ] 3.6 Bump the Requirements module release, regenerate registry metadata,
  and satisfy checksum/signature policy without changing unrelated modules.

## 4. Paired CLI handoff and verification

- [ ] 4.1 Publish the immutable released commit SHA and command compatibility
  evidence for the paired CLI change.
- [ ] 4.2 Run focused command/script/workflow tests, `hatch run format`,
  `type-check`, `lint`, `yaml-lint`, `check-bundle-imports`, signature/version
  verification, `contract-test`, `smart-test`, and changed-line SpecFact code
  review; resolve all findings.
- [x] 4.3 Update Requirements and contributor documentation with source modes,
  sidecar semantics, report locations, proof limits, and AI remediation flow.
- [x] 4.4 Run `openspec validate requirements-06-evidence-enforcement --strict`
  and record passing evidence in `TDD_EVIDENCE.md`.

## 5. Delivery

- [ ] 5.1 Commit, push, and open a PR to `dev` with the paired-core
  compatibility and release evidence.
- [ ] 5.2 After merge, coordinate the CLI fixture update, then archive with
  `openspec archive requirements-06-evidence-enforcement`.
