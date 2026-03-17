## Context

The `backlog add` command in `backlog_core/commands/add.py` creates new ADO work items by calling `graph_adapter.create_issue()`. The current implementation hardcodes a type mapping in `AdoAdapter.create_issue()`:

```python
type_mapping = {
    "epic": "Epic",
    "feature": "Feature",
    "story": "User Story",
    "user story": "User Story",
    "task": "Task",
    "bug": "Bug",
    "spike": "Task",
}
```

However, Azure DevOps projects can use different process templates (Scrum, Agile, Basic, CMMI) with different work item type names. Scrum uses "Product Backlog Item" instead of "User Story". The `map-fields` command already creates `work_item_type_mappings` in `.specfact/templates/backlog/field_mappings/ado_custom.yaml`, but `backlog add` ignores this configuration.

The `backlog refine` command already respects these mappings when updating existing work items. The `AdoFieldMapper` class provides `map_work_item_type()` method for this purpose.

## Goals / Non-Goals

**Goals:**
- Make `backlog add` respect `work_item_type_mappings` from the field mapping config
- Ensure consistency between `backlog add` (create) and `backlog refine` (update) behavior
- Support project-specific work item type names (Scrum, Agile, etc.)

**Non-Goals:**
- Change the mapping file format or location
- Modify how `map-fields` generates mappings
- Add new work item types beyond what's configurable

## Decisions

**Decision 1**: Load `AdoFieldMapper` in `backlog add` and use it to resolve work item types
- Rationale: `AdoFieldMapper` already handles custom mappings and has the `map_work_item_type()` method
- Implementation: Initialize `AdoFieldMapper` with the custom mapping file path from config

**Decision 2**: Modify type resolution in `create_issue` payload preparation
- Current: Hardcoded `type_mapping` dict in `AdoAdapter.create_issue()`
- New: Pass mapped type through payload, or handle mapping in the adapter using `AdoFieldMapper`
- Rationale: Minimize changes to `AdoAdapter` by using existing mapper infrastructure

**Decision 3**: Keep fallback to hardcoded defaults when no custom mapping exists
- Rationale: Maintains backward compatibility for projects without custom mappings
- Implementation: Try custom mapping first, fall back to current behavior if not found

## Risks / Trade-offs

- [Risk] Projects without custom mappings still use hardcoded "User Story" which may fail for Scrum templates
  → Mitigation: Document that `map-fields` should be run to generate proper mappings
- [Risk] Mapping config may be out of sync with actual ADO project
  → Mitigation: 400 errors from ADO will indicate invalid work item type; user can re-run `map-fields`
