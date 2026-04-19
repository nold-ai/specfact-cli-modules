## 1. Branch and dependency guardrails

- [ ] 1.1 Create `chore/finops-01-module-cost-outcome` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Confirm paired core changes `telemetry-01-opentelemetry-default-on` and `finops-01-telemetry-and-outcomes` are available and document the minimum required `core_compatibility`.
- [ ] 1.3 Before implementation, create or sync public GitHub tracking metadata for this change, including parent linkage, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency checks.

## 2. Spec and failing-test preparation

- [ ] 2.1 Finalize `specs/finops-cost-outcome-module/spec.md`.
- [ ] 2.2 Write failing tests for provider cost normalization, local fallback accounting, and evidence-file generation.
- [ ] 2.3 Write failing tests for deterministic outcome classification and report rendering.
- [ ] 2.4 Capture failing-first evidence in `openspec/changes/finops-01-module-cost-outcome/TDD_EVIDENCE.md`.

## 3. Bundle implementation

- [ ] 3.1 Scaffold `packages/specfact-finops/` with manifest, Typer entrypoints, provider adapters, and reporting helpers.
- [ ] 3.2 Implement collectors that normalize cost/token data into the paired core FinOps evidence/report contracts.
- [ ] 3.3 Implement deterministic outcome classification plus evidence write paths compatible with downstream knowledge and enterprise analytics.
- [ ] 3.4 Update registry metadata, docs references, signatures, and any import allowlists required by the new bundle.

## 4. Verification and delivery

- [ ] 4.1 Re-run targeted tests and affected package coverage; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Run quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, then `hatch run contract-test` and relevant `hatch run smart-test` / `hatch run test`.
- [ ] 4.3 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate every finding, and record the command plus timestamp in `TDD_EVIDENCE.md`.
- [ ] 4.4 Run `openspec validate finops-01-module-cost-outcome --strict`.
- [ ] 4.5 Open the modules PR to `dev`, cross-link paired telemetry/FinOps changes, and note any deferred provider integrations as follow-up issues.
