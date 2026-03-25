## Context

The modules repo currently packages official bundles as mostly code-and-manifest payloads. At the same time, the core CLI repository still carries workflow prompt templates under `resources/prompts`, and core init logic separately copies backlog field mapping templates from a core-owned `resources/templates/backlog/field_mappings` location.

That split is no longer coherent after bundle extraction:

- prompts belong to the workflow bundles, not to core lifecycle commands
- backlog field mapping templates belong to the backlog bundle, not to core
- prompt companion assets such as `shared/cli-enforcement.md` travel with those prompts and must remain resolvable after export
- installed bundle packages need a stable on-disk resource layout so core CLI can discover resources from installed bundles rather than from fallback core directories

The audit result is explicit: the official bundle package directories in `specfact-cli-modules` do not currently contain `resources/prompts` trees, so a modules-repo change is required.

## Goals / Non-Goals

**Goals:**

- package prompt templates inside the owning official bundles
- package prompt companion assets required by those prompts, starting with `resources/prompts/shared/cli-enforcement.md`
- package other module-owned resources that still live in core, beginning with the full backlog field mapping template seed set
- standardize a resource layout that can be discovered from installed bundle roots
- prove that signing and verification remain resource-aware and fail when bundled resources change without a version/signature update

**Non-Goals:**

- implement the core CLI discovery/export logic itself; that belongs to specfact-cli
- redesign prompt content or workflow semantics
- move resources that are still genuinely core-owned, such as global signing keys, unless ownership analysis proves otherwise

## Decisions

### 1. Co-locate resources under each owning bundle package

Each official bundle should carry a `resources/` subtree inside its package directory for assets that travel with that bundle. At minimum this change covers:

- prompt templates for bundle-owned workflows
- prompt companion resources referenced by those prompt templates
- backlog field mapping templates under the backlog bundle, including non-ADO templates copied into workspace state

This keeps installation, packaging, signature, and ownership boundaries aligned.

### 2. Treat resource changes as bundle payload changes

The modules repo already computes integrity hashes from full module payloads. This change will preserve that behavior and add tests/documentation so resource additions and edits are explicitly covered by version-bump and signature workflows.

### 3. Keep the contract with core CLI path-based and package-rooted

The bundle packages should expose resources through a stable package-root layout rather than through bespoke manifest-only indirection. Core CLI can then discover `resources/prompts`, prompt companion files under the same prompt root, or other agreed subpaths from installed bundle roots.

## Risks / Trade-offs

- `[Resource ownership audit misses a leftover core-owned file]` -> record the audited inventory and explicit keep-in-core list in a change-local audit artifact.
- `[Prompts copy successfully but relative includes break]` -> treat prompt companion files as part of the prompt payload contract, not optional extras.
- `[Bundle packages gain more non-code files]` -> accept slightly larger artifacts in exchange for correct ownership and install behavior.
- `[Core and modules repos drift on expected resource paths]` -> keep the path contract explicit and cross-reference the specfact-cli packaging change.

## Migration Plan

1. Audit which current core resources are bundle-owned.
2. Move prompt templates, prompt companion assets, and backlog field mapping templates into the owning bundle packages.
3. Add tests for package-resource presence and integrity/version-bump enforcement.
4. Update docs/manifests as needed and sync dependency notes back to the core packaging change.

## Open Questions

- Whether any non-backlog template directories under core resources also belong to extracted bundles after the audit in `RESOURCE_OWNERSHIP_AUDIT.md`.
- Whether bundle manifests should later gain explicit resource catalog metadata, or whether stable subpaths are sufficient for the first iteration.
