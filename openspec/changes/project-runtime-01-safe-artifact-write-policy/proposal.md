# Change: Runtime Adoption Of Safe Artifact Write Policy

## Why

SpecFact bundle runtime code should normally keep its local state inside `.specfact/` and avoid mutating user-owned repository artifacts. The existing change overreaches by implying a repo-wide generic safe-write layer for every runtime writer; the practical need is narrower: sanctioned external touchpoints outside `.specfact` need the core safe-write contract, while managed artifacts inside `.specfact` need explicit ownership rules so user-tuned config is preserved and fully owned state remains deterministic.

## What Changes

- **NEW**: Define a runtime artifact boundary policy that distinguishes sanctioned external user-owned artifacts outside `.specfact` from SpecFact-managed artifacts inside `.specfact`.
- **NEW**: Require any sanctioned runtime touchpoint outside `.specfact` to reuse the paired core safe-write contract from `specfact-cli` rather than introducing a second generic modules-side abstraction.
- **NEW**: Define `.specfact` ownership classes for bundle runtime artifacts: fully owned generated state may update deterministically, while user-tuned config files must preserve unrelated keys or sections.
- **EXTEND**: Narrow first-adopter scope to practical backlog bundle paths such as `.specfact/backlog-config.yaml`, mapping files under `.specfact/templates/backlog/`, and sync-managed state/output paths.
- **EXTEND**: Bundle docs and prompts to state preservation guarantees only for sanctioned external touchpoints and ownership semantics for `.specfact` artifacts.

## Capabilities

### New Capabilities

- `runtime-artifact-write-safety`: Boundary-based runtime write policy for modules bundles, covering sanctioned external user-owned artifact touchpoints and ownership-aware writes inside `.specfact`.

### Modified Capabilities

- `backlog-add`: backlog config and mapping writes under `.specfact` must preserve unrelated user-managed settings while keeping fully owned generated artifacts deterministic.
- `backlog-sync`: sync-managed artifacts must distinguish fully owned `.specfact` state from explicit external output targets and avoid silent overwrite of user-owned paths.

## Impact

- Affected code: first-adopter backlog runtime paths in `packages/specfact-backlog/`, especially config, mapping, and sync-managed local artifact writes; broader project/spec bundle adoption is deferred until a generic paired core API exists.
- Affected docs: backlog bundle docs on modules.specfact.io covering config, sync/export, and local artifact ownership expectations.
- Integration points: depends on the paired core change `specfact-cli/openspec/changes/profile-04-safe-project-artifact-writes` only for sanctioned external user-owned artifacts outside `.specfact`.
- Dependencies: does not introduce a generic modules-side safe-write framework; future broad runtime adoption may need a follow-up core API expansion instead of stretching this change further.

## Source Tracking

- **GitHub Issue**: #177
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/177
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: open
- **Parent Feature**: #161
- **Parent Feature URL**: https://github.com/nold-ai/specfact-cli-modules/issues/161
- **Related Core Change**: specfact-cli#487 bug context and paired core change `profile-04-safe-project-artifact-writes`
