## Why

Issue #49 reports that Azure DevOps mapped provider fields lose type information between `specfact backlog map-fields` and `specfact backlog add`. This causes required non-string custom fields (boolean/numeric) to be sent as strings and rejected by ADO.

Source tracking: https://github.com/nold-ai/specfact-cli-modules/issues/49

## What Changes

- Persist selected work-item required field type metadata when running `specfact backlog map-fields`.
- Use persisted field type metadata during `specfact backlog add` provider field resolution so `--provider-field` values are coerced to ADO runtime types.
- Validate invalid typed values early with clear CLI errors before adapter API calls.
- Add regression coverage for metadata persistence and typed coercion behavior.

## Capabilities

### Modified Capabilities
- `backlog-add`: mapped ADO provider fields are coerced using persisted field type metadata.
