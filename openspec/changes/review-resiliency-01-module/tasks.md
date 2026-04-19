## 1. Branch and dependency guardrails

- [ ] 1.1 Create `chore/review-resiliency-01-module` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Confirm paired core change `review-resiliency-01-contracts` is available for integration and document the minimum required `core_compatibility`.
- [ ] 1.3 Before implementation begins, create or sync public GitHub tracking metadata for this change, including parent linkage, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency checks.

## 2. Spec and failing-test preparation

- [ ] 2.1 Finalize `specs/review-resiliency-module/spec.md` with command, rule-pack, and evidence scenarios.
- [ ] 2.2 Write failing tests for bundle manifest loading, command registration, and findings-to-report mapping.
- [ ] 2.3 Write failing tests for static resiliency rule execution and opt-in probe gating behavior.
- [ ] 2.4 Capture failing-first evidence in `openspec/changes/review-resiliency-01-module/TDD_EVIDENCE.md`.

## 3. Bundle implementation

- [ ] 3.1 Scaffold `packages/specfact-review-resiliency/` with `module-package.yaml`, Typer entrypoints, and packaged rule resources.
- [ ] 3.2 Implement adapters that translate analyzer output into the paired core resiliency findings/report contracts.
- [ ] 3.3 Add optional probe adapters behind explicit flags/profile configuration without changing default offline-safe behavior.
- [ ] 3.4 Update registry metadata, signing inputs, docs references, and any import allowlists required by the new bundle.

## 4. Verification and delivery

- [ ] 4.1 Re-run targeted tests and broader affected package coverage; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Run quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, then `hatch run contract-test` and relevant `hatch run smart-test` / `hatch run test`.
- [ ] 4.3 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate every finding, and record the command plus timestamp in `TDD_EVIDENCE.md`.
- [ ] 4.4 Run `openspec validate review-resiliency-01-module --strict`.
- [ ] 4.5 Open the modules PR to `dev`, cross-link the paired core change, and note any deferred probe integrations as follow-up issues.
