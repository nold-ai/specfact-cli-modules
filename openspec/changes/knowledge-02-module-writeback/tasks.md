# 1. Branch and dependency guardrails

- [ ] 1.1 Create `chore/knowledge-02-module-writeback` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Confirm paired core change `knowledge-02-preflight-context-assembly` and module dependency `knowledge-01-module-memory-runtime` are available and document the minimum required `core_compatibility`.
- [ ] 1.3 Before implementation, create or sync public GitHub tracking metadata for this change, including parent linkage, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency checks.
- [ ] 1.4 Refresh the GitHub hierarchy cache (`python scripts/sync_github_hierarchy_cache.py`) and verify parent/child plus blocker metadata matches the authoritative GitHub graph before execution starts.

## 2. Spec and failing-test preparation

- [ ] 2.1 Finalize `specs/knowledge-writeback/spec.md`.
- [ ] 2.2 Write failing tests for preview generation, deterministic output manifests, and target-adapter selection.
- [ ] 2.3 Write failing tests for file-target safety behavior and draft CodeRabbit output generation.
- [ ] 2.4 Capture failing-first evidence in `openspec/changes/knowledge-02-module-writeback/TDD_EVIDENCE.md`.

## 3. Bundle implementation

- [ ] 3.1 Scaffold `packages/specfact-knowledge-writeback/` with manifest, Typer entrypoints, target adapters, and preview helpers.
- [ ] 3.2 Implement adapters for the first approved writeback targets using rules sourced from `specfact-knowledge`.
- [ ] 3.3 Add deterministic output-manifest generation plus preview/dry-run behavior for every target.
- [ ] 3.4 Update registry metadata, docs references, signing inputs, and any import allowlists required by the new bundle.

## 4. Verification and delivery

- [ ] 4.1 Re-run targeted tests and affected package coverage; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Run quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, then `hatch run contract-test` and relevant `hatch run smart-test` / `hatch run test`.
- [ ] 4.3 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate every finding, and record the command plus timestamp in `TDD_EVIDENCE.md`.
- [ ] 4.4 Run `openspec validate knowledge-02-module-writeback --strict`.
- [ ] 4.5 Open the modules PR to `dev`, cross-link paired knowledge changes, and note any deferred target adapters as follow-up issues.
