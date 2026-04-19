## 1. Branch and dependency guardrails

- [ ] 1.1 Create `chore/architecture-02-module-well-architected` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Confirm paired core change `architecture-02-well-architected-review` is available and document the minimum required `core_compatibility`.
- [ ] 1.3 Before implementation, create or sync public GitHub tracking metadata for this change, including parent linkage, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency checks.

## 2. Spec and failing-test preparation

- [ ] 2.1 Finalize `specs/architecture-well-architected-module/spec.md`.
- [ ] 2.2 Write failing tests for boundary-rule evaluation, interface-diff classification, and ADR traceability ingestion.
- [ ] 2.3 Write failing tests proving `ALLOWED_IMPORTS.md`-style rules can be translated into portable bundle resources.
- [ ] 2.4 Capture failing-first evidence in `openspec/changes/architecture-02-module-well-architected/TDD_EVIDENCE.md`.

## 3. Bundle implementation

- [ ] 3.1 Scaffold `packages/specfact-architecture/` with manifest, Typer entrypoints, analyzer adapters, and rule resources.
- [ ] 3.2 Implement import-graph, interface-diff, and ADR-traceability adapters that normalize into the paired core architecture findings/report contracts.
- [ ] 3.3 Integrate repository boundary rules derived from `ALLOWED_IMPORTS.md` and package any provider-specific defaults needed for initial language support.
- [ ] 3.4 Update registry metadata, docs references, signatures, and any import allowlists required by the new bundle.

## 4. Verification and delivery

- [ ] 4.1 Re-run targeted tests and affected package coverage; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Run quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, then `hatch run contract-test` and relevant `hatch run smart-test` / `hatch run test`.
- [ ] 4.3 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate every finding, and record the command plus timestamp in `TDD_EVIDENCE.md`.
- [ ] 4.4 Run `openspec validate architecture-02-module-well-architected --strict`.
- [ ] 4.5 Open the modules PR to `dev`, cross-link the paired core architecture change, and note any deferred analyzer providers as follow-up issues.
