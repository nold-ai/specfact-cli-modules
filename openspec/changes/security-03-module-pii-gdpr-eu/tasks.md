# 1. Branch and dependency guardrails

- [ ] 1.1 Create `chore/security-03-module-pii-gdpr-eu` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Confirm paired core changes `security-01-unified-findings-model` and `security-02-eu-gdpr-baseline` are available and document the minimum required `core_compatibility`.
- [ ] 1.3 Before implementation, create or sync public GitHub tracking metadata for this change, including parent linkage, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency checks.

## 2. Spec and failing-test preparation

- [ ] 2.1 Finalize `specs/privacy-gdpr-module/spec.md`.
- [ ] 2.2 Write failing tests for PII detection normalization, GDPR article/lawful-basis mapping, and redaction-safe evidence handling.
- [ ] 2.3 Write failing tests for EU residency checks and command behavior across policy modes.
- [ ] 2.4 Capture failing-first evidence in `openspec/changes/security-03-module-pii-gdpr-eu/TDD_EVIDENCE.md`.

## 3. Bundle implementation

- [ ] 3.1 Scaffold `packages/specfact-pii-gdpr/` with manifest, Typer entrypoints, detector adapters, and bundled rule resources.
- [ ] 3.2 Implement normalization into the paired core privacy/GDPR findings/report contracts with redaction-safe evidence references.
- [ ] 3.3 Integrate shared policy/profile handling for lawful-basis and residency checks plus optional knowledge evidence hooks.
- [ ] 3.4 Verify compatibility with `nold-ai/specfact-cli` whenever changing shared privacy/GDPR findings or report contracts by running and reviewing the paired public artifacts/tests in specfact-cli and confirming any required adapter changes or test updates before PR handoff.
- [ ] 3.5 Update registry metadata, docs references, and any import allowlists required by the new bundle. Note: signature artifacts are produced by publish automation and validated by CI gates; do not manually commit signature files.

## 4. Verification and delivery

- [ ] 4.1 Re-run targeted tests and affected package coverage; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Run quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, then `hatch run contract-test` and relevant `hatch run smart-test` / `hatch run test`.
- [ ] 4.3 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate every finding, and record the command plus timestamp in `TDD_EVIDENCE.md`.
- [ ] 4.4 Run `openspec validate security-03-module-pii-gdpr-eu --strict`.
- [ ] 4.5 Open the modules PR to `dev`, cross-link paired privacy/security changes, and note any deferred detector providers as follow-up issues.