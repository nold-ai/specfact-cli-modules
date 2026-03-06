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
