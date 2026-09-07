## Why

A successful unchanged hierarchy sync currently leaves its freshness metadata stale. Bootstrap then treats the cache as expired and repeats live GitHub lookups despite a successful read.

## What Changes

- Renew the state-file freshness timestamp after every successful sync, including an unchanged hierarchy fingerprint.
- Preserve the unchanged markdown cache payload to avoid unnecessary file churn.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `github-hierarchy-cache`: Successful unchanged refreshes provide fresh machine-readable cache state.

## Impact

Updates `scripts/sync_github_hierarchy_cache.py`, its focused unit tests, and GitHub tracking issue #457. No module, registry, or published API changes.

## Source Tracking

- **GitHub Issue**: [#457](https://github.com/nold-ai/specfact-cli-modules/issues/457)
- **Parent Feature**: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163)
- **Last Synced Status**: open / Todo (verified 2026-08-31)
