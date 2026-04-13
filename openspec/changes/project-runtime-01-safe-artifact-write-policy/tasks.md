## 1. Branch and paired-change setup

- [ ] 1.1 Create `bugfix/project-runtime-01-safe-artifact-write-policy` in a dedicated worktree from `origin/dev` and bootstrap the worktree environment.
- [ ] 1.2 Confirm the paired core change `profile-04-safe-project-artifact-writes` is implemented or available for integration and document the minimum required core compatibility.
- [ ] 1.3 If a modules-side tracking issue is created, link it back to `specfact-cli#487` and the paired core issue/change for traceability.

## 2. Runtime tests and failing evidence

- [ ] 2.1 Inventory first-adopter bundle commands that write persistent user-project artifacts and select the initial runtime adoption scope.
- [ ] 2.2 Write tests from the new scenarios proving bundle commands preserve unrelated user content, fail safely on unsupported merges, and surface explicit replacement behavior when required.
- [ ] 2.3 Run the targeted runtime tests before implementation and record failing commands/timestamps in `openspec/changes/project-runtime-01-safe-artifact-write-policy/TDD_EVIDENCE.md`.

## 3. Runtime safe-write adoption

- [ ] 3.1 Integrate the core safe-write helper into the selected runtime package commands with explicit ownership metadata and required contract decorators on any new public APIs.
- [ ] 3.2 Update package code paths for the first adopters so they no longer perform raw overwrite behavior against user-project artifacts.
- [ ] 3.3 Adjust package metadata, compatibility declarations, and any supporting docs/prompts required by the new runtime dependency on the core safe-write contract.

## 4. Verification, docs, and release hygiene

- [ ] 4.1 Re-run the targeted runtime tests and any broader affected package coverage, then record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Update affected modules docs to explain preservation guarantees and explicit replacement semantics for adopted commands.
- [ ] 4.3 Run quality gates in order: `hatch run format` → `hatch run type-check` → `hatch run lint` → `hatch run yaml-lint` → `hatch run check-bundle-imports` → `hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`, then bump package versions and re-sign changed manifests if verification failed for that reason, then `hatch run contract-test`, then the relevant `hatch run smart-test` / `hatch run test` coverage for changed packages.
- [ ] 4.4 Run `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`, remediate all findings (or document a rare approved exception), attach or cite the resulting `.specfact/code-review.json`, and record the exact review command and timestamp in `TDD_EVIDENCE.md` or PR notes (last governance action before merge).
- [ ] 4.5 Open the modules PR to `dev`, cross-link the paired core PR, and note any deferred runtime adoption paths as follow-up issues if the initial scope is intentionally limited.
