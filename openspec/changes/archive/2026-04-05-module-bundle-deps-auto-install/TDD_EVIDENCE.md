# TDD evidence — module-bundle-deps-auto-install

## Tests

- Added `tests/unit/test_registry_manifest_bundle_dependencies.py`:
  - `test_registry_bundle_dependencies_match_manifests` — every registry module with a local `module-package.yaml` must have matching `bundle_dependencies`.
  - `test_official_bundle_dependency_graph_is_acyclic` — no cycles among `nold-ai/*` edges in `registry/index.json`.
- Ran: `.venv/bin/pytest tests/unit/test_registry_manifest_bundle_dependencies.py` — **pass** (2 tests).
- Ran: `.venv/bin/pytest tests/unit/docs/test_bundle_overview_cli_examples.py` — **pass** (after overview doc update).

## Implementation

- `packages/specfact-code-review/module-package.yaml`: `bundle_dependencies` includes `nold-ai/specfact-codebase`; version **0.46.0** (minor bump per design).
- `registry/index.json` + `registry/modules/specfact-code-review-0.46.0.tar.gz` (+ `.sha256`) aligned with publish workflow layout.
- `docs/bundles/code-review/overview.md`: prerequisites note peer dependency / auto-install behavior.

## Signing (required before CI merge)

Manifest integrity was generated with **`hatch run sign-modules -- --allow-unsigned`** (checksum only) because the local signing key is encrypted and no passphrase was available in this environment.

**Before opening the PR or merging**, sign with the org private key so CI passes `verify-modules-signature --require-signature`:

```bash
hatch run sign-modules -- \
  --key-file "${SPECFACT_MODULE_PRIVATE_SIGN_KEY_FILE:-$HOME/.specfact/sign-keys/module-signing-private.pem}" \
  packages/specfact-code-review/module-package.yaml \
  --payload-from-filesystem
```

Then re-run:

```bash
hatch run verify-modules-signature -- --require-signature --payload-from-filesystem
```

If the manifest checksum changes after signing, rebuild the registry tarball and refresh `registry/index.json` checksum for `specfact-code-review-0.46.0.tar.gz` (same Python step as publish workflow) or re-run the publish automation.

## Quality gates (2026-04-02, worktree)

- `hatch run format` — pass  
- `hatch run yaml-lint` — pass  
- `hatch run type-check` (scoped + full lint path) — pass via `hatch run lint`  
- `hatch run lint` — pass  
- `python scripts/verify-modules-signature.py --payload-from-filesystem` — pass (all 6 manifests)  
- `python scripts/verify-modules-signature.py --require-signature --payload-from-filesystem` — **fails until manifest is signed** (expected until signing step above)  
- `hatch run contract-test` — pass  
- `hatch run smart-test` — pass  
- `hatch run test` — pass  
- `hatch run specfact code review run --json --out .specfact/code-review.json --scope changed` — not run (SpecFact CLI: `Command 'code' is not installed`); complete before PR per `tasks.md` 4.3.
