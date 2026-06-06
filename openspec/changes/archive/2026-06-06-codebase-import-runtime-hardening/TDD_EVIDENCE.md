# TDD evidence — codebase-import-runtime-hardening

## Timestamp

2026-04-20 (worktree `cursor/codebase-import-runtime-hardening-98df`)

## Failing-before tests

- `pytest tests/unit/specfact_project/test_import_runtime_policy.py tests/unit/test_bundle_resource_payloads.py`
  - Failing import-policy tests prove the shared traversal helper does not exist yet: `ModuleNotFoundError: No module named 'specfact_project.utils.import_path_policy'`.
  - Failing analyzer-progress test proves `CodeAnalyzer.analyze()` still counts raw discovered files instead of the filtered analyzable set for Phase 3 progress totals.
  - Failing bundle-resource tests prove required project runtime templates are not packaged under `packages/specfact-project/resources/templates/` and therefore are absent from the built artifact payload.

## Passing-after tests

- `pytest tests/unit/specfact_project/test_import_runtime_policy.py tests/unit/test_bundle_resource_payloads.py`
  - `21 passed` after introducing the shared import traversal policy, filtered progress totals, packaged runtime templates, and runtime template-resolution coverage.

## Publish pre-check

- `python3 scripts/publish_module.py --bundle specfact-project`
  - Passed after bumping `packages/specfact-project/module-package.yaml` to `0.41.4`.

## GitHub tracking notes

- Parent Feature created: `specfact-cli-modules#234`
- Change issue created: `specfact-cli-modules#235`
- Labels, issue types, and native parent/sub-issue links were applied successfully.
- ProjectV2 assignment could not be updated with the available repository token because GitHub returned `Resource not accessible by personal access token` for `addProjectV2ItemById`.
