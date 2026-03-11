## Design

`map-fields` already fetches required-field metadata per selected work item type. Extend that pipeline to also collect each required field's ADO type (e.g. `boolean`, `integer`, `double`) from work item type field metadata and follow-up field metadata calls.

Persist this metadata in backlog provider settings under a per-work-item-type dictionary so add-time resolution can read it without additional API calls.

In `backlog add` ADO provider-field resolution:

1. Load required refs + allowed values + type metadata for the resolved create work item type.
2. Convert override/prompt values for mapped required fields using the field type map.
3. Keep existing top-level canonical behavior unchanged.
4. Raise a validation error when values cannot be converted (e.g. `Custom.Toggle=Yes` for boolean).

Supported coercions:
- boolean: `true/false`, `1/0`, `yes/no`, `on/off` (case-insensitive)
- integer: Python int conversion
- number/double/float/decimal: Python float conversion
- everything else: preserve string
