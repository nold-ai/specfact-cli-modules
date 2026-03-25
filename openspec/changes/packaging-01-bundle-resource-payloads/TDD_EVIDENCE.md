# TDD evidence — packaging-01-bundle-resource-payloads

## Failing-first (design)

- Added `tests/unit/test_bundle_resource_payloads.py` asserting stable `packages/<bundle>/resources/...` paths for audited prompts, `shared/cli-enforcement.md`, backlog field-mapping seeds (including non-ADO `github_custom.yaml`), integrity payload sensitivity to resource edits, and version-bump helper behavior.

## Passing (implementation)

- 2026-03-25: `python -m pytest tests/unit/test_bundle_resource_payloads.py` — 9 passed.
- Bundles now ship resources under each module package root (`resources/prompts`, `resources/templates/backlog/field_mappings`) with a mirror under `src/specfact_backlog/resources/...` for `find_package_resources_path("specfact_backlog", ...)`.
- `specfact_backlog.backlog.field_mapping_resources.load_ado_framework_template_config` prefers backlog bundle + module-root paths before legacy `specfact_cli` templates (logic extracted from `commands.py` for clarity and reviewability).
- Docs: `docs/authoring/publishing-modules.md` documents bundle-owned `resources/` and version/signature expectations.

## packaging-02 path contract (task 4.2)

- **Module install layout**: `.specfact/modules/<bundle>/resources/prompts`, `.specfact/modules/<bundle>/resources/templates/backlog/field_mappings` (module root = directory containing `module-package.yaml`).
- **Python package layout (backlog)**: `specfact_backlog/resources/templates/backlog/field_mappings` for installed-package resolution.

## docs-08 … docs-12 (task 4.4)

- User-facing path updates for bundle-owned prompts/templates are expected to land in the active docs changes (`docs-08`–`docs-12`); this change does not add a separate docs change id.

## Signing note

- Local signing used `scripts/sign-modules.py --allow-unsigned --payload-from-filesystem` when encrypted private key passphrase was unavailable.
- Before opening a PR, re-run signing with the repository private key so `integrity.signature` is present for `verify-modules-signature.py --require-signature`.
