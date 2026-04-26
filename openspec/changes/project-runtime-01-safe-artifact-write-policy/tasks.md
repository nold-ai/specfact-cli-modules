## 1. Branch and paired-change setup

- [x] 1.1 Create `bugfix/project-runtime-01-safe-artifact-write-policy` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [x] 1.2 Refresh proposal, design, specs, and tasks to narrow scope to sanctioned external user-owned artifacts and ownership-aware `.specfact` writes.
- [x] 1.3 Confirm the paired core change `profile-04-safe-project-artifact-writes` is implemented or available for integration, and document that current compatibility applies only to sanctioned external artifacts outside `.specfact`.

## 2. Runtime tests and failing evidence

- [x] 2.1 Inventory first-adopter backlog bundle paths and select the initial scope: `.specfact/backlog-config.yaml`, field-mapping files, and sync-managed baseline/output paths.
- [x] 2.2 Write tests from the refined scenarios proving `.specfact` config updates preserve unrelated settings and explicit external sync targets are not silently overwritten.
- [x] 2.3 Run the targeted runtime tests before implementation and record failing commands/timestamps in `openspec/changes/project-runtime-01-safe-artifact-write-policy/TDD_EVIDENCE.md`.

## 3. Runtime safe-write adoption

- [x] 3.1 Implement ownership-aware local write helpers for the selected backlog paths without introducing a repo-wide generic modules-side safe-write framework.
- [x] 3.2 Update backlog config and mapping code paths so partially owned `.specfact` config preserves unrelated settings instead of rewriting whole files.
- [x] 3.3 Update backlog sync managed-state paths to distinguish fully owned `.specfact` artifacts from explicit external output targets, and reuse paired core safe-write behavior only where an external user-owned path is touched.
- [x] 3.4 Adjust package metadata, compatibility declarations, and any supporting docs/prompts only if selected runtime paths require new paired core APIs.

## 4. Verification, docs, and release hygiene

- [x] 4.1 Re-run the targeted runtime tests and any broader affected package coverage, then record passing evidence in `TDD_EVIDENCE.md`.
- [x] 4.2 Update affected modules docs to explain `.specfact` ownership semantics, preserved config behavior, and any explicit replacement rules for sanctioned external paths.
- [x] 4.3 Run quality gates in order: `hatch run format` → `hatch run type-check` → `hatch run lint` → `hatch run yaml-lint` → `hatch run check-bundle-imports` → `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump` (no `--require-signature` for pre-merge dev PRs; signature is enforced by CI on push/approval), then bump package versions and re-sign changed manifests if verification failed for that reason, then `hatch run contract-test`, then the relevant `hatch run smart-test` / `hatch run test` coverage for changed packages.
- [x] 4.4 Run `hatch run specfact code review run --level error --json --out .specfact/code-review.json --scope full`, remediate all findings (or document a rare approved exception), attach or cite the resulting `.specfact/code-review.json`, and record the exact review command and timestamp in `TDD_EVIDENCE.md` or PR notes (last governance action before merge).
- [x] 4.5 Modules PR #246 merged to `dev`; PR #248 open to `main`. Paired core change: `specfact-cli` `profile-04-safe-project-artifact-writes` (core PR cross-link applies only for the sanctioned external-artifact contract; no core PR number recorded here as the core side is tracked in `specfact-cli`). Deferred follow-up: a broader generic modules-side safe-write framework is not part of this change; if future bundles need the same pattern they should open a new core expansion item.
