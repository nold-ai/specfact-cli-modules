## Failing Evidence

Added regression tests first, then ran:

```bash
hatch run pytest tests/unit/specfact_backlog/unit/test_add_command_ado_provider_fields.py tests/unit/specfact_backlog/test_map_fields_command.py -q
```

Result:
- 3 failed:
  - boolean provider override was still sent as string
  - invalid boolean override was accepted
  - map-fields did not persist required field type metadata

## Passing Evidence

After implementation, reran targeted and broader checks:

```bash
hatch run pytest tests/unit/specfact_backlog/unit/test_add_command_ado_provider_fields.py tests/unit/specfact_backlog/test_map_fields_command.py -q
```

Result:
- `15 passed`

```bash
hatch test -v
```

Result:
- fails in this environment due hatch-test env missing specfact-cli-linked dependencies (`ModuleNotFoundError` for `specfact_cli`, `typer`, `yaml`)

```bash
hatch run format
hatch run lint
hatch run type-check
hatch run test
```

Result:
- `format`: pass
- `lint`: pass
- `type-check`: `0 errors, 0 warnings, 0 notes`
- `test`: `218 passed, 16 skipped`
