# 1. Branch and dependency guardrails

- [ ] 1.1 Create `chore/security-02-module-license-compliance` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Confirm paired core changes `security-01-unified-findings-model` and `security-02-eu-gdpr-baseline` are available, document the minimum required `core_compatibility` against both, and capture any sequencing assumptions in `TDD_EVIDENCE.md`.
- [ ] 1.3 Before implementation, create or sync public GitHub tracking metadata for this change, including parent linkage, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency checks.

## 2. Spec and failing-test preparation

- [ ] 2.1 Finalize `specs/license-compliance-module/spec.md`.
- [ ] 2.2 Write failing tests for SBOM ingestion, SPDX normalization, and policy evaluation outcomes.
- [ ] 2.3 Write failing tests for exception handling and command exit/report behavior across policy modes.
- [ ] 2.4 Capture failing-first evidence in `openspec/changes/security-02-module-license-compliance/TDD_EVIDENCE.md`.

## 3. Bundle implementation

- [ ] 3.1 Scaffold `packages/specfact-license-compliance/` with manifest, Typer entrypoints, and bundled policy resources.
- [ ] 3.2 Implement SBOM ingestion and SPDX normalization adapters that emit the findings/report contracts from `security-01-unified-findings-model`.
- [ ] 3.3 Integrate policy-mode handling, remediation messaging, and optional SBOM sharing hooks for adjacent security workflows.
- [ ] 3.4 Update registry metadata, docs references, signing inputs, and any import allowlists required by the new bundle.

## 4. Verification and delivery

- [ ] 4.1 Re-run targeted tests and affected package coverage; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Run quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, then `hatch run contract-test` and relevant `hatch run smart-test` / `hatch run test`.
- [ ] 4.3 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate every finding, and record the command plus timestamp in `TDD_EVIDENCE.md`.
- [ ] 4.4 Run `openspec validate security-02-module-license-compliance --strict`.
- [ ] 4.5 Open the modules PR to `dev`, cross-link paired security changes, and note any deferred SBOM-provider work as follow-up issues.
