# TDD Evidence

## Failing

Command:

```bash
hatch run test -- tests/unit/specfact_backlog/unit/test_add_command.py tests/unit/specfact_backlog/unit/test_adapter_create_issue.py -q
```

Observed failures before implementation:

- `tests/unit/specfact_backlog/unit/test_add_command.py::test_backlog_add_ado_resolves_custom_work_item_type_mapping`
  Expected payload `work_item_type == "Product Backlog Item"`, got `None`.

## Passing

Focused verification:

```bash
hatch run python -m pytest tests/unit/specfact_backlog/unit/test_add_command.py -q
```

Result:

- `20 passed in 0.37s`

Full regression verification:

```bash
hatch run test -- -q
```

Result:

- `205 passed, 16 skipped in 10.25s`
