## Why

Enterprise Azure DevOps and GitHub backlog setups can require provider-specific custom fields that are discovered and persisted by `specfact backlog map-fields`. The current backlog command surface does not consistently treat that mapping config as the source of truth for create and writeback payloads, so commands can still submit incomplete provider payloads and fail with HTTP 400.

## What Changes

- Modify backlog command payload assembly to resolve required provider fields from persisted `backlog map-fields` configuration before making ADO or GitHub write calls.
- Add an explicit command-line override mechanism for mapped provider fields so teams can supply or replace resolved values at invocation time when needed.
- Make interactive flows prompt for missing required mapped provider fields and make non-interactive flows fail fast with a clear validation error before provider API calls.
- Reuse the same provider-required field resolution rules across `backlog add` and backlog writeback commands instead of hardcoding per-command canonical fields.

## Capabilities

### New Capabilities
- `backlog-provider-writeback`: shared provider-required field resolution and validation for backlog write commands using persisted field-mapping config plus explicit overrides

### Modified Capabilities
- `backlog-add`: backlog add must use persisted provider mapping metadata as the default source of required provider fields for ADO and GitHub create flows

## Impact

- Affected code: `packages/specfact-backlog/src/specfact_backlog/backlog_core/commands/add.py`, `packages/specfact-backlog/src/specfact_backlog/backlog/commands.py`, provider mapping helpers under `packages/specfact-backlog/src/specfact_backlog/backlog/mappers/`, and backlog command tests.
- User-facing impact: backlog commands stop silently dropping required mapped provider fields and instead resolve them from config, prompt for them interactively, or fail early in non-interactive mode.
- Risk area: command option surface may need a generic provider-field override syntax that works across both ADO and GitHub.
