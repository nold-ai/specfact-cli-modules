## Why

Bundle-owned prompt templates and other workflow resources still live in the core CLI repository, while the bundle packages that actually own those workflows ship without those assets. That breaks package ownership, prevents `specfact init ide` and install flows from discovering the right source payloads, and leaves resource movement dependent on core-only fallbacks instead of bundle packaging.

## What Changes

- Add bundle-packaged resource payloads for official bundles so prompts and other module-owned assets ship from the bundle that owns them.
- Move workflow prompt templates out of `specfact-cli/resources/prompts` into the corresponding bundle packages in `specfact-cli-modules`.
- Move any other module-owned assets that still live in core, starting with backlog field mapping templates, into the owning bundle package.
- Preserve prompt companion assets such as `resources/prompts/shared/cli-enforcement.md` so exported prompts do not ship broken relative references.
- Audit and migrate the complete backlog workspace-template seed set required by init/install flows, not just `ado_*.yaml`.
- Define and test a consistent package layout for bundle resources so the core CLI can discover them from installed bundle locations.
- Lock resource payloads into signing, verification, and publish/version-bump workflows so bundle updates are resource-aware.
- Keep `specfact-cli` runtime discovery, source selection, and `specfact init ide` export orchestration out of scope here; that work is tracked in `specfact-cli` change `init-ide-prompt-source-selection` (`nold-ai/specfact-cli#382`).

## Capabilities

### New Capabilities
- `bundle-packaged-resources`: Official bundle packages ship their prompt templates and other module-owned resources within the bundle package tree.
- `resource-aware-integrity`: Bundle resource payloads participate in signing, verification, and version-bump enforcement so resource changes are treated as publishable bundle changes.

### Modified Capabilities

None.

## Impact

- Affected code: `packages/specfact-*/`, module manifests, packaging/publish/signature scripts, and modules-repo tests.
- Affected systems: bundle packaging, registry publish validation, signature verification, and core CLI installed-resource discovery.
- Audit artifact: `openspec/changes/packaging-01-bundle-resource-payloads/RESOURCE_OWNERSHIP_AUDIT.md`
- Cross-repo dependency: this change provides the resource payloads consumed by specfact-cli change `packaging-02-cross-platform-runtime-and-module-resources` and the narrowed core-side orchestration/selectability change `init-ide-prompt-source-selection` (`nold-ai/specfact-cli#382`).

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #101
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/101>
- **Last Synced Status**: proposed
- **Sanitized**: false
