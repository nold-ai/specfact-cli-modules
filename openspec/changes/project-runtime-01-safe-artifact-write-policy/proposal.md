# Change: Runtime Adoption Of Safe Artifact Write Policy

## Why

Core can define safer init/setup behavior, but the broader trust problem remains if bundle runtime commands in `specfact-cli-modules` still overwrite or rewrite user-project artifacts ad hoc. To make issue [specfact-cli#487](https://github.com/nold-ai/specfact-cli/issues/487) impossible by design rather than by one-off fix, runtime package commands that write local artifacts need to adopt the same safe-write contract and conflict semantics.

## What Changes

- **NEW**: Introduce a runtime-facing artifact write adapter/utility layer for bundle packages that classifies local writes as create-only, mergeable, append-only, or explicit-replace.
- **NEW**: Standardize backup, recovery metadata, and dry-run/preview surfaces for bundle commands that emit or mutate project artifacts.
- **NEW**: Define adoption guidance so bundle authors declare ownership boundaries for every local artifact path they write.
- **EXTEND**: Update initial adopter package commands in `specfact-project`, `specfact-spec`, and other bundle flows that currently write directly into target repos to use the safe-write utility instead of raw overwrite calls.
- **EXTEND**: Bundle docs and prompts to state the new preservation guarantees and when explicit force/replace semantics are required.

## Capabilities

### New Capabilities
- `runtime-artifact-write-safety`: Shared runtime safety contract for bundle commands that create or mutate project artifacts in user repositories.

### Modified Capabilities
- `backlog-add`: local export helpers and related artifact generation must use the runtime safe-write contract when updating project files.
- `backlog-sync`: runtime sync/export flows must avoid silent local overwrites and surface preview-or-conflict behavior consistently.

## Impact

- Affected code: bundle runtime helpers in `packages/specfact-project/`, `packages/specfact-spec/`, and any command packages that currently call `write_text` directly against user project files.
- Affected docs: relevant bundle docs on modules.specfact.io covering setup, sync/export, and local artifact generation.
- Integration points: depends on the paired core change `specfact-cli/openspec/changes/profile-04-safe-project-artifact-writes` for the authoritative policy and terminology.
- Dependencies: may require a new modules-side feature issue if no existing feature cleanly groups cross-package local-write safety work.

## Source Tracking

- **GitHub Issue**: #177
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/177
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: open
- **Parent Feature**: #161
- **Parent Feature URL**: https://github.com/nold-ai/specfact-cli-modules/issues/161
- **Related Core Change**: specfact-cli#487 bug context and paired core change `profile-04-safe-project-artifact-writes`
