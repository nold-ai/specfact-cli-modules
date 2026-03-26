# TDD evidence — packaging-01-bundle-resource-payloads

## Failing-first (design)

- Added `tests/unit/test_bundle_resource_payloads.py` asserting stable `packages/<bundle>/resources/...` paths for audited prompts, `shared/cli-enforcement.md`, backlog field-mapping seeds (including non-ADO `github_custom.yaml`), integrity payload sensitivity to resource edits, and version-bump helper behavior.
- 2026-03-26: `python3 -m pytest tests/unit/test_bundle_resource_payloads.py -q` — failed as expected after extending coverage to backlog prompts.
  - Missing source payload: `packages/specfact-backlog/resources/prompts/specfact.backlog-add.md`
  - Missing module-root discovery path: `packages/specfact-backlog/resources/prompts/specfact.backlog-refine.md`
  - Missing artifact payload entries under `specfact-backlog/resources/prompts/`

## Passing (implementation)

- 2026-03-25: `python -m pytest tests/unit/test_bundle_resource_payloads.py` — 9 passed.
- 2026-03-26: `python3 -m pytest tests/unit/test_bundle_resource_payloads.py -q` — 13 passed.
- `packages/specfact-backlog/resources/prompts/` now ships the restored backlog prompt inventory: `specfact.backlog-add.md`, `specfact.backlog-daily.md`, `specfact.backlog-refine.md`, and `specfact.sync-backlog.md`.
- `packages/specfact-backlog/resources/prompts/shared/cli-enforcement.md` now ships with the backlog prompt payload so restored relative links resolve after export.
- `packages/specfact-backlog/module-package.yaml` was bumped to `0.41.15` and re-signed after the prompt payload changed.
- Bundles now ship resources under each module package root (`resources/prompts`, `resources/templates/backlog/field_mappings`) with a mirror under `src/specfact_backlog/resources/...` for `find_package_resources_path("specfact_backlog", ...)`.
- `specfact_backlog.backlog.field_mapping_resources.load_ado_framework_template_config` prefers backlog bundle + module-root paths before legacy `specfact_cli` templates (logic extracted from `commands.py` for clarity and reviewability).
- Docs: `docs/authoring/publishing-modules.md` documents bundle-owned `resources/` and version/signature expectations.

## Artifact verification (task 4.6)

- 2026-03-26: built a workflow-shaped backlog artifact at `/tmp/specfact-backlog-0.41.15.tar.gz` using the same inclusion/exclusion rules as `.github/workflows/publish-modules.yml`.
- Verified the archive contains:
  - `specfact-backlog/resources/prompts/specfact.backlog-add.md`
  - `specfact-backlog/resources/prompts/specfact.backlog-daily.md`
  - `specfact-backlog/resources/prompts/specfact.backlog-refine.md`
  - `specfact-backlog/resources/prompts/specfact.sync-backlog.md`
  - `specfact-backlog/resources/prompts/shared/cli-enforcement.md`

## Cross-repo prompt discovery/export verification (task 4.7)

- Added `test_core_prompt_discovery_finds_installed_backlog_bundle` in `tests/unit/test_bundle_resource_payloads.py`.
- The test copies `packages/specfact-backlog/` into a temporary install-like module root, patches installed `specfact_cli.utils.ide_setup._module_discovery_roots(...)`, and verifies:
  - `discover_prompt_sources_catalog(...)` includes `nold-ai/specfact-backlog`
  - the discovered prompt set includes the restored backlog prompt filenames
  - installed core export writes IDE prompt files for the backlog source segment and matches `expected_ide_prompt_export_paths(...)`

## packaging-02 path contract (task 4.2)

- **Module install layout**: `.specfact/modules/<bundle>/resources/prompts`, `.specfact/modules/<bundle>/resources/templates/backlog/field_mappings` (module root = directory containing `module-package.yaml`).
- **Python package layout (backlog)**: `specfact_backlog/resources/templates/backlog/field_mappings` for installed-package resolution.

## docs-08 … docs-12 (task 4.4)

- User-facing path updates for bundle-owned prompts/templates are expected to land in the active docs changes (`docs-08`–`docs-12`); this change does not add a separate docs change id.

## Signing note

- Local signing used `scripts/sign-modules.py --allow-unsigned --payload-from-filesystem` when encrypted private key passphrase was unavailable.
- Before opening a PR, re-run signing with the repository private key so `integrity.signature` is present for `verify-modules-signature.py --require-signature`.
