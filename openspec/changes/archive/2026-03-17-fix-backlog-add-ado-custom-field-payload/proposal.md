## Why

`specfact backlog add --adapter ado` can resolve a project-specific work item type, but it does not propagate mapped required custom fields into the create payload. This leaves Azure DevOps non-interactive create flows broken for projects that enforce required custom fields configured through backlog field mappings.

## What Changes

- MODIFY: Update ADO backlog creation so canonical custom fields mapped in `.specfact/templates/backlog/field_mappings/ado_custom.yaml` are included in the create payload.
- MODIFY: Ensure `backlog add` uses the same mapping contract for ADO create that `map-fields` and refine/update paths already establish.
- EXTEND: Add regression coverage for ADO create payload construction, including interactive and non-interactive invocations that should converge on the same provider payload shape.
- EXTEND: Document the integration boundary with the downstream ADO adapter so work item type and mapped field emission stay consistent.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `backlog-add`: ADO backlog creation must include mapped required custom fields and preserve parity between interactive and non-interactive create flows.

## Impact

- Affected specs: `openspec/specs/backlog-add/spec.md`
- Affected code: `packages/specfact-backlog/src/specfact_backlog/backlog_core/commands/add.py`
- Affected tests: `tests/unit/specfact_backlog/unit/test_add_command.py`
- Integration points: downstream ADO create handling in `specfact-cli` must continue honoring explicit `work_item_type` and mapped provider fields
- User-facing impact: ADO projects with required custom fields can create backlog items successfully from CLI automation and interactive flows

## Source Tracking

- **GitHub Issue**: #42
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/42
- **Last Synced Status**: open
- **Sanitized**: true
