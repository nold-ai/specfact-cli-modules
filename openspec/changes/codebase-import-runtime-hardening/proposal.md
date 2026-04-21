## Why

`specfact code import` currently walks too much of a repository before it applies ignore rules, which causes it to scan virtual environments, build outputs, hidden tooling directories, and other heavyweight artifacts that users never intended to import. The same runtime area also ships incomplete resources: project-bundle generators reference Jinja2 templates that are not packaged with the module artifact, so installed workflows can fail even when the command surface is otherwise available.

## What Changes

- **NEW**: Add a shared codebase-import runtime policy that prunes hidden and heavyweight directories before traversal, supports a repo-local `.specfact/.specfactignore`, and emits targeted warnings when unusually large artifact trees are encountered.
- **NEW**: Replace fixed-duration import expectations with progress derived from discovered-versus-processed work so long-running imports report remaining time from live scan data instead of a hard-coded optimism bias.
- **EXTEND**: Align all import traversal phases (`count`, analyzer discovery, relationship extraction, and AI context loading) to the same ignore policy so progress totals and scanned files reflect the real implementation scope.
- **EXTEND**: Ship the project bundle's runtime Jinja2 templates as bundled resources, resolve them from packaged paths, and add tests that fail if required generator templates are missing from the module artifact.
- **EXTEND**: Update import documentation to explain the default ignore behavior, `.specfact/.specfactignore`, large-artifact warnings, and the new ETA semantics.

## Capabilities

### New Capabilities
- `codebase-import-runtime`: Default ignore policy, warning surfaces, and dynamic progress estimation for `specfact code import` runtime scans.

### Modified Capabilities
- `bundle-packaged-resources`: Project-bundle runtime generator templates become required packaged resources alongside prompts and other module-owned assets.

## Impact

- Affected code: `packages/specfact-project/` import runtime, scanners, analyzers, generator resource resolution, and bundled resources; `packages/specfact-codebase/` command entry points where import behavior is surfaced.
- Affected tests: targeted import-runtime, generator-resource, and bundle-payload coverage under `tests/`.
- Affected docs: codebase/project bundle import docs on modules.specfact.io, especially `docs/bundles/project/import-migration.md` and related workflow guidance.
- Release impact: patch version bumps and signature/registry updates for module artifacts whose manifests or packaged resources change.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Modules Epic**: [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162)
- **Parent Feature**: [#234](https://github.com/nold-ai/specfact-cli-modules/issues/234)
- **GitHub Issue**: [#235](https://github.com/nold-ai/specfact-cli-modules/issues/235)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/235>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
