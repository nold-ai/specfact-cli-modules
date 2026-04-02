# Change: Declare peer bundle dependencies for auto-install

## Why

Several official bundles share a top-level command group (for example `specfact code …`) but only declare `commands: [code]` in the manifest. Installing a single bundle (such as `nold-ai/specfact-code-review`) therefore does not pull in sibling bundles that register the rest of that group’s commands. Users hit missing subcommands until they manually install `nold-ai/specfact-codebase`. Other bundles already declare `bundle_dependencies` (codebase, spec, govern depend on project); code-review is inconsistent and should declare the peer bundle(s) needed for a complete `code` group experience.

## What Changes

- Set `bundle_dependencies` on `nold-ai/specfact-code-review` to include `nold-ai/specfact-codebase` so the CLI can auto-install the codebase bundle (and its existing dependency on project) when users install code review.
- Align `registry/index.json` metadata for `nold-ai/specfact-code-review` with the updated manifest (`bundle_dependencies` field).
- Bump `specfact-code-review` semver (patch or minor per scope of manifest-only vs. user-visible install behavior) and refresh integrity checksums/signatures per publish workflow.
- Add or extend tests that assert manifest and registry rows stay consistent for declared bundle dependencies.
- Optionally document the dependency in bundle overview or install docs if user-facing guidance should mention the relationship.

## Capabilities

### New Capabilities

- `module-bundle-dependencies`: Official module manifests and registry entries declare `bundle_dependencies` so SpecFact CLI can install required peer bundles for full command-group coverage; code-review lists codebase as a dependency.

### Modified Capabilities

- (none) — no existing `openspec/specs/` requirement files change; this change introduces a new capability spec.

## Impact

- `packages/specfact-code-review/module-package.yaml` — `bundle_dependencies` populated.
- `registry/index.json` — matching `bundle_dependencies` for the code-review module entry.
- Published artifact tarball and signatures after version bump; `.github/workflows/publish-modules.yml` path unchanged except normal publish flow.
- `tests/` — assertions for registry/manifest parity if not already covered.
- Potential docs: `docs/bundles/code-review/overview.md` or reference pages if we surface the dependency to users.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #135
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/135
- **Last Synced Status**: synced
- **Sanitized**: true
