## 1. Governance and paired-contract readiness

- [x] 1.1 Create modules issue #346 under parent feature #161 with `enhancement`,
  `project`, `openspec`, and `change-proposal` labels and SpecFact CLI project
  assignment.
- [x] 1.2 Record the completed #168 follow-up relationship and the observed
  official Spec Kit 0.12.15 scaffold behavior in the proposal and design.
- [x] 1.3 Link paired core issue nold-ai/specfact-cli#648 (follow-up to #350);
  record its release version as this change's blocker before implementation.
- [x] 1.4 Recheck current GitHub issue state, parent, labels, project assignment,
  blockers, and active-work concurrency before implementation starts.

## 2. Core contract and source-readiness tests

Completed in paired core issue [nold-ai/specfact-cli#648](https://github.com/nold-ai/specfact-cli/issues/648),
released in SpecFact CLI 0.53.1; these tasks remain here as integration traceability.

- [x] 2.1 In the paired core change, specify the structured source-readiness
  result and diagnostics: `incomplete-source-template`, `source-incomplete`,
  `source-invalid`, and `upstream-validator-unavailable`.
- [x] 2.2 Add a pinned fixture for the official Spec Kit scaffold and tests that
  reject its unresolved placeholders and `NEEDS CLARIFICATION` markers with
  zero normalized records.
- [x] 2.3 Add core tests that accept a completed native Spec Kit feature with
  stable IDs, source hash provenance, given/when/then rules, and idempotency.
- [x] 2.4 Add core tests for strict OpenSpec validator failure, required
  validator absence, and portable import when policy does not require the CLI.
- [x] 2.5 Add byte-identical upstream-source tests and capture failing-first
  evidence before any production change.

## 3. Modules integration and regression tests

- [x] 3.1 Raise `specfact-requirements` core compatibility to `>=0.53.1,<1.0.0`
  after the paired core readiness contract is available on core `dev`.
- [x] 3.2 Add failing module command tests proving rejected OpenSpec and Spec Kit
  sources report core diagnostics unchanged, exit non-zero, and do not create a
  requirements sidecar.
- [x] 3.3 Add module command tests proving completed sources retain current
  import counts, stable records, read-only behavior, and re-import idempotency.
- [x] 3.4 Implement thin runtime delegation and command rendering without local
  parsing, placeholder detection, hashing, or upstream-validator policy logic.
- [x] 3.5 Run targeted tests and record failing-before and passing-after output
  in `TDD_EVIDENCE.md`.

## 4. Documentation and release preparation

- [x] 4.1 Update Requirements module documentation with source-readiness
  diagnostics, portable versus required upstream validation, and remediation
  guidance for unfinished sources.
- [x] 4.2 Bump the Requirements module patch version, regenerate payload
  checksum/signature, and update registry artifacts only after behavior tests
  pass. GitHub signing/publish automation performs the signed-artifact and
  registry update after this PR is accepted.
- [x] 4.3 Run formatting, lint, type, YAML, signature, contract, smart-test,
  and targeted test gates.
- [x] 4.4 Run a fresh SpecFact code review JSON report after the last proposal,
  test, implementation, or documentation edit; resolve every finding and record
  the command and result in `TDD_EVIDENCE.md`.

## 5. Delivery

- [x] 5.1 Add a `requirements-evidence.yaml` mapping for this change's imported
  stable requirement to the existing source-readiness runtime and command tests.
- [x] 5.2 Add an actual-source regression test proving this change and #352
  produce a passed Requirements evidence verdict together.
- [x] 5.3 Capture failing-before and passing-after evidence for the missing
  mapping repair, including strict OpenSpec validation and source read-only
  checks.
- [x] 5.4 Synchronize and reopen issue #346 with the final core dependency,
  scope, and acceptance evidence.
- [x] 5.5 Merge modules PR #360 to `dev` with the paired-core release
  requirement, test evidence, signature verification, and documentation
  updates on 2026-07-26.
