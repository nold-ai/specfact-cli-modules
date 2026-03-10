# TDD Evidence

## Failing

Command:

```bash
hatch run test -- tests/unit/specfact_backlog/unit/test_add_command.py tests/unit/specfact_backlog/unit/test_adapter_create_issue.py -q
```

Observed failures before implementation:

- `tests/unit/specfact_backlog/unit/test_add_command.py::test_backlog_add_ado_resolves_custom_work_item_type_mapping`
  Expected payload `work_item_type == "Product Backlog Item"`, got `None`.
- `tests/unit/specfact_backlog/unit/test_adapter_create_issue.py::test_ado_create_issue_prefers_explicit_work_item_type`
  Expected create URL to target `$Product%20Backlog%20Item`, got `$User Story`.

## Passing

Focused verification:

```bash
hatch run python -m pytest tests/unit/specfact_backlog/unit/test_add_command.py tests/unit/specfact_backlog/unit/test_adapter_create_issue.py -q
```

Result:

- `26 passed in 0.45s`

Full regression verification:

```bash
hatch run test -- -q
```

Result:

- `206 passed, 16 skipped in 10.29s`
