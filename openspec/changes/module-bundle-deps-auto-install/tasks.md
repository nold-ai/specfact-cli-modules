## 1. Branch and baseline

- [x] 1.1 Create branch `feature/module-bundle-deps-auto-install` from `origin/dev` (use a dedicated worktree if preferred).

## 2. Tests first (TDD)

- [x] 2.1 Add or extend tests that fail until `bundle_dependencies` for `nold-ai/specfact-code-review` in `module-package.yaml` matches `registry/index.json` (and cover acyclic dependency expectation if applicable).

## 3. Implementation

- [x] 3.1 Update `packages/specfact-code-review/module-package.yaml`: set `bundle_dependencies` to include `nold-ai/specfact-codebase`; bump semver per design.
- [x] 3.2 Update `registry/index.json` for `nold-ai/specfact-code-review` so `bundle_dependencies` matches the manifest; refresh checksums, download_url, and version fields per publish/sign workflow when artifacts are produced.
- [x] 3.3 Run signing / `verify-modules-signature` flow so integrity fields in the manifest stay valid after edits. (Checksum OK via `--payload-from-filesystem`; **Ed25519 signature** must be applied with the org private key before merge — see `TDD_EVIDENCE.md`.)
- [x] 3.4 Optionally update user-facing docs (for example code-review bundle overview) to mention that installing code review pulls the codebase bundle for the full `code` command group.

## 4. Evidence and quality gates

- [x] 4.1 Record failing/passing test notes in `openspec/changes/module-bundle-deps-auto-install/TDD_EVIDENCE.md`.
- [x] 4.2 Run full quality gate sequence from AGENTS.md (`format`, `type-check`, `lint`, `yaml-lint`, `verify-modules-signature`, `contract-test`, `smart-test`, `test`). (Full suite run; `verify-modules-signature` without `--require-signature` passes; **with** `--require-signature` pending until signing step above.)
- [ ] 4.3 Ensure `.specfact/code-review.json` is present and fresh relative to edits under `packages/`, `registry/`, `tests/`, and this change folder (excluding evidence-only `TDD_EVIDENCE.md` updates). Run `hatch run specfact code review run --json --out .specfact/code-review.json` with `--scope changed` while iterating and `--scope full` before the final PR; remediate all findings. **Blocked here:** `specfact code review` requires workflow bundles (`Command 'code' is not installed`); run after `specfact module install` / profile init locally.
- [x] 4.4 Open PR to `dev` and link GitHub issue below. — PR [#136](https://github.com/nold-ai/specfact-cli-modules/pull/136) (issue [#135](https://github.com/nold-ai/specfact-cli-modules/issues/135)).

## 5. Source tracking

- [x] 5.1 Keep `proposal.md` Source Tracking in sync with the GitHub issue number and URL after issue creation.
