## Pre-Implementation Failing Run

- Date: 2026-03-06
- Command: `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run contract-test`
- Result: failed
- Summary:
  - `tests/unit/specfact_backlog/test_map_fields_command.py::test_map_fields_reports_progress_for_selected_work_item_type_metadata`
  - `tests/unit/specfact_backlog/test_refine_adapter_contract.py::test_fetch_backlog_items_accepts_core_backlog_adapter`
  - Both failures resolved `specfact_backlog.backlog.commands` from `~/.specfact/modules/specfact-backlog/...` instead of the local workspace bundle.

## Post-Implementation Passing Run

- Date: 2026-03-06
- Command: `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run pytest tests/unit/test_local_bundle_source_alignment.py tests/unit/specfact_backlog/test_map_fields_command.py tests/unit/specfact_backlog/test_refine_adapter_contract.py -q`
- Result: passed
- Summary:
  - New bootstrap sanitizer regression test passed.
  - The backlog progress-output regression and core-adapter acceptance regression passed with local workspace bundle imports.

## Full Gate Validation

- `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run type-check`: passed
- `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run lint`: passed
- `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run yaml-lint`: passed
- `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run contract-test`: passed
- `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run smart-test`: passed
- `openspec validate backlog-bundle-local-source-alignment --strict`: passed
