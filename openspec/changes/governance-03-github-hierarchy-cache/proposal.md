## Why

The modules repository now has its own Epic and Feature hierarchy, but contributors still have to query GitHub directly to rediscover parent Features and Epics before syncing OpenSpec changes. That creates unnecessary API traffic and makes cross-repo governance slower and less deterministic than it should be.

## What Changes

- Add a deterministic repo-local hierarchy cache generator for `specfact-cli-modules` Epic and Feature issues.
- Persist a repo-local markdown hierarchy cache at `.specfact/backlog/github_hierarchy_cache.md` (ignored; not committed) with issue number, title, brief summary, labels, and hierarchy relationships, plus a companion fingerprint/state file `.specfact/backlog/github_hierarchy_cache_state.json` so the sync can exit quickly when Epic and Feature metadata has not changed.
- Update governance instructions in `AGENTS.md` for modules-side GitHub issue setup to consult the cache first and rerun sync only when needed.
- Keep the modules-side cache behavior aligned with the paired core change so both repos expose the same planning lookup pattern.

## Capabilities

### New Capabilities
- `github-hierarchy-cache`: Deterministic synchronization of GitHub Epic and Feature hierarchy metadata into a repo-local OpenSpec markdown cache for low-cost parent and planning lookups.

### Modified Capabilities
- `backlog-sync`: Modules-side backlog and change-sync workflows must be able to resolve current Epic and Feature planning metadata from the repo-local cache before performing manual GitHub lookups.

## Impact

- Affected code: new script and tests under `scripts/` and `tests/`, plus governance guidance in `AGENTS.md`.
- Affected workflow: OpenSpec change creation and modules-side GitHub issue parenting become cache-first instead of lookup-first.
- Cross-repo impact: this change must stay aligned with `specfact-cli` so both repos use the same hierarchy-cache operating model.

## Source Tracking

- GitHub Issue: [#178](https://github.com/nold-ai/specfact-cli-modules/issues/178)
- Parent Feature: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163)
- Paired core (specfact-cli): `governance-02-github-hierarchy-cache` — tracked in `specfact-cli` `openspec/CHANGE_ORDER.md` with [specfact-cli#491](https://github.com/nold-ai/specfact-cli/issues/491) (distinct from the older `governance-02-exception-management` / `#248` row in the same file).
