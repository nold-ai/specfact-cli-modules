## 1. Branch and dependency guardrails

- [ ] 1.1 Create `chore/knowledge-01-module-memory-runtime` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Confirm paired core change `knowledge-01-distillation-engine` is available and document the minimum required `core_compatibility`.
- [ ] 1.3 Before implementation, create or sync public GitHub tracking metadata for this change, including parent linkage, labels, project assignment, blockers, blocked-by relationships, and `in progress` concurrency checks.

## 2. Spec and failing-test preparation

- [ ] 2.1 Finalize `specs/knowledge-memory-runtime/spec.md`.
- [ ] 2.2 Write failing tests for filesystem layout creation, markdown-graph indexing, search behavior, and command registration.
- [ ] 2.3 Write failing tests for evidence, learning, and rule file lifecycle handling under `.specfact/memory/`.
- [ ] 2.4 Capture failing-first evidence in `openspec/changes/knowledge-01-module-memory-runtime/TDD_EVIDENCE.md`.

## 3. Bundle implementation

- [ ] 3.1 Scaffold `packages/specfact-knowledge/` with manifest, Typer entrypoints, filesystem backend helpers, and default resources.
- [ ] 3.2 Implement the markdown-graph backend and CLI commands that satisfy the paired core `MemoryBackend` expectations.
- [ ] 3.3 Add deterministic repo-layout, gitignore, search, and status behavior for memory content without introducing a required vector store.
- [ ] 3.4 Update registry metadata, docs references, signatures, and any import allowlists required by the new bundle.

## 4. Verification and delivery

- [ ] 4.1 Re-run targeted tests and affected package coverage; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Run quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, then `hatch run contract-test` and relevant `hatch run smart-test` / `hatch run test`.
- [ ] 4.3 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate every finding, and record the command plus timestamp in `TDD_EVIDENCE.md`.
- [ ] 4.4 Run `openspec validate knowledge-01-module-memory-runtime --strict`.
- [ ] 4.5 Open the modules PR to `dev`, cross-link the paired core knowledge change, and note any deferred optional adapters as follow-up issues.
