# 1. Branch and dependency guardrails

- [ ] 1.1 Create `chore/security-01-module-sast-sca-secret` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Verify that both referenced core changes (`security-01-unified-findings-model` and `policy-02-packs-and-modes`) exist and are merged in `specfact-cli` before binding core compatibility. Document the minimum required `core_compatibility` versions in `TDD_EVIDENCE.md` and record any sequencing notes.
- [ ] 1.3 Before implementation, create or sync public GitHub tracking metadata for this change, including parent linkage, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency checks.

## 2. Spec and failing-test preparation

- [ ] 2.1 Finalize `specs/security-sast-sca-secret-module/spec.md`.
- [ ] 2.2 Write failing adapter tests for Semgrep, dependency-risk, SBOM, and secret-scan result normalization.
- [ ] 2.3 Write failing tests for command-mode behavior across advisory, mixed, and hard policy modes.
- [ ] 2.4 Capture failing-first evidence in `openspec/changes/security-01-module-sast-sca-secret/TDD_EVIDENCE.md`.

## 3. Bundle implementation

- [ ] 3.1 Scaffold `packages/specfact-security/` with manifest, Typer entrypoints, and scanner/resource wiring.
- [ ] 3.2 Implement adapters that normalize scanner output into the paired core security findings/report contracts.
- [ ] 3.3 Integrate profile-aware execution controls, JSON/markdown reporting, and optional knowledge evidence handoff.
- [ ] 3.4 Update registry metadata, docs references, signing inputs, and any import allowlists required by the new bundle.

## 4. Verification and delivery

- [ ] 4.1 Re-run targeted tests and affected package coverage; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Run quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, then `hatch run contract-test` and relevant `hatch run smart-test` / `hatch run test`.
- [ ] 4.3 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate every finding, and record the command plus timestamp in `TDD_EVIDENCE.md`.
- [ ] 4.4 Run `openspec validate security-01-module-sast-sca-secret --strict`.
- [ ] 4.5 Open the modules PR to `dev`, cross-link paired security changes, and call out any deferred scanner providers as follow-up issues.