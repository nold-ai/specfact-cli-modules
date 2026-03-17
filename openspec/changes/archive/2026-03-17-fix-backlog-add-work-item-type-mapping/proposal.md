## Why

The `specfact backlog add` command fails when creating "story" type items in Azure DevOps projects using the Scrum template. The command hardcodes "story" → "User Story" mapping, but Scrum projects use "Product Backlog Item". The `map-fields` command already creates proper `work_item_type_mappings` in the config, but `backlog add` ignores this mapping and uses its own hardcoded values.

## What Changes

- Modify `backlog add` command to read `work_item_type_mappings` from `.specfact/templates/backlog/field_mappings/ado_custom.yaml` (via `AdoFieldMapper`)
- Use the configured mapping to translate canonical types ("story", "task", "bug") to provider-specific work item types
- Fall back to hardcoded defaults only when no custom mapping exists
- Ensure consistency with `backlog refine` command which already uses this mapping for updates

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `backlog-add`: REQUIREMENTS updated to include work_item_type_mappings from config when creating ADO work items

## Impact

- Affected: `backlog_core/commands/add.py`, `backlog/mappers/ado_mapper.py`
- ADO adapter integration in specfact-cli-modules
- User-facing: Backlog add will respect project-specific work item type mappings
