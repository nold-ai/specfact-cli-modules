# 1. Branch and dependency guardrails

- [ ] 1.1 Create `chore/enterprise-02-module-audit-client` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Confirm paired core change `enterprise-02-rbac-and-audit-trail` and upstream sequencing from `enterprise-01-module-policy-client` are available and document the minimum required `core_compatibility`.
- [ ] 1.3 Before implementation, create or sync public GitHub tracking metadata for this change, including parent linkage, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency checks.

## 2. Spec and failing-test preparation

- [ ] 2.1 Finalize `specs/enterprise-audit-client/spec.md`.
- [ ] 2.2 Write failing tests for audit payload signing, privacy-aware serialization, local queue persistence, and retry/inspection behavior.
- [ ] 2.3 Write failing tests for governance-action mappings into the paired core audit schema.
- [ ] 2.4 Capture failing-first evidence in `openspec/changes/enterprise-02-module-audit-client/TDD_EVIDENCE.md`.

## 3. Bundle implementation

- [ ] 3.1 Scaffold `packages/specfact-enterprise-audit/` with manifest, Typer entrypoints, queue helpers, and signing utilities.
- [ ] 3.2 Implement audit event preparation and queueing aligned with the paired core audit contracts.
- [ ] 3.3 Add inspection/retry commands plus deterministic local receipt metadata without requiring immediate network delivery.
- [ ] 3.4 Update registry metadata, docs references, signing inputs, and any import allowlists required by the new bundle.

## 4. Verification and delivery

- [ ] 4.1 Re-run targeted tests and affected package coverage; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Run quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, then `hatch run contract-test` and relevant `hatch run smart-test` / `hatch run test`.
- [ ] 4.3 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate every finding, and record the command plus timestamp in `TDD_EVIDENCE.md`.
- [ ] 4.4 Run `openspec validate enterprise-02-module-audit-client --strict`.
- [ ] 4.5 Open the modules PR to `dev`, cross-link paired enterprise changes, and note any deferred delivery/reconciliation behavior as follow-up issues.
