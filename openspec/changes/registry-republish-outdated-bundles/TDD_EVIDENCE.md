## Pre-implementation failing run

- **Timestamp (UTC):** 2026-03-06T10:52:00Z
- **Command:** `hatch run pytest tests/unit/test_publish_module_script.py tests/unit/test_publish_bundle_selection.py -q`
- **Result:** FAIL

### Failure summary

- `tests/unit/test_publish_module_script.py` failed during collection because there is no importable script module surface for explicit registry-baseline comparison yet.
- `tests/unit/test_publish_bundle_selection.py` failed during collection because there is no reusable bundle-selection helper that can union changed bundles with registry-outdated bundles.
- This is the expected red phase for tasks 1.1 and 1.2.

## Post-implementation passing run

- **Timestamp (UTC):** 2026-03-06T10:54:00Z
- **Command:** `hatch run pytest tests/unit/test_publish_module_script.py tests/unit/test_publish_bundle_selection.py -q`
- **Result:** PASS

### Passing summary

- The publish pre-check script now supports an explicit `--registry-index-path` baseline, so version comparison can target the exposed registry state instead of only the checked-out branch index.
- The workflow bundle-selection helper now unions diff-selected bundles with bundles whose manifest versions are ahead of the registry baseline and preserves inclusion reasons.

## Direct wrapper execution regression

- **Timestamp (UTC):** 2026-03-06T19:55:00Z
- **Pre-fix command:** `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run pytest tests/unit/test_publish_module_script.py -q`
- **Pre-fix result:** FAIL

### Pre-fix failure summary

- `test_publish_module_wrapper_runs_when_executed_as_script` failed with `ModuleNotFoundError: No module named 'scripts'`.
- This matched the GitHub Actions publish workflow path, which executes `python scripts/publish-module.py` directly.

- **Post-fix command:** `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run pytest tests/unit/test_publish_module_script.py tests/unit/test_publish_bundle_selection.py -q`
- **Post-fix result:** PASS

### Post-fix passing summary

- The compatibility wrapper now bootstraps the repository root before importing `scripts.publish_module`, so direct script execution works in the publish workflow environment.

## Dev baseline loop prevention regression

- **Timestamp (UTC):** 2026-03-06T20:10:00Z
- **Pre-fix command:** `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run pytest tests/unit/test_publish_registry_baseline.py -q`
- **Pre-fix result:** FAIL

### Pre-fix failure summary

- `test_determine_registry_baseline_ref_uses_dev_for_dev_pushes` failed during collection because there was no baseline-selection helper.
- The workflow therefore defaulted to `main` as the outdated-bundle baseline even on `dev` publish runs, which allowed repeated auto publish PRs after registry-only merges to `dev`.

- **Post-fix command:** `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run pytest tests/unit/test_publish_registry_baseline.py tests/unit/test_publish_bundle_selection.py tests/unit/test_publish_module_script.py -q`
- **Post-fix result:** PASS

### Post-fix passing summary

- The workflow now chooses `dev` as the effective outdated-bundle baseline on `dev` pushes and falls back to the default branch only for other branches.
- Existing registry-outdated and publish-wrapper tests still pass with the new baseline-selection behavior.
