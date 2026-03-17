# TDD Evidence

## Failing

Command:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages:/home/dom/.local/lib/python3.11/site-packages:/home/dom/git/nold-ai/specfact-cli/src \
HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run pytest tests/unit/specfact_backlog/unit/test_add_command.py -q -k "ado_forwards_mapped_custom_fields_for_create or ado_interactive_matches_non_interactive_provider_fields"
```

Observed failures before implementation:

- `test_backlog_add_ado_forwards_mapped_custom_fields_for_create`
  Expected `payload["provider_fields"]["fields"]` to contain mapped ADO custom fields, got `None`.
- `test_backlog_add_ado_interactive_matches_non_interactive_provider_fields`
  Expected both interactive and non-interactive flows to emit the same mapped ADO `provider_fields`, got `None` for the interactive payload.

## Passing

Focused verification:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages:/home/dom/.local/lib/python3.11/site-packages:/home/dom/git/nold-ai/specfact-cli/src \
HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run pytest tests/unit/specfact_backlog/unit/test_add_command.py -q -k "ado_forwards_mapped_custom_fields_for_create or ado_interactive_matches_non_interactive_provider_fields"
```

Result:

- `2 passed, 20 deselected in 0.20s`

Broader regression verification:

```bash
PYTHONPATH=/usr/lib/python3/dist-packages:/home/dom/.local/lib/python3.11/site-packages:/home/dom/git/nold-ai/specfact-cli/src \
HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run pytest tests/unit/specfact_backlog/unit/test_add_command.py -q
```

Result:

- `22 passed in 0.47s`
