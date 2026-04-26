# TDD Evidence

## Failing Evidence

- `2026-04-24T23:34:27+02:00`
- Command:
  `hatch run pytest tests/unit/specfact_backlog/test_map_fields_command.py tests/unit/specfact_backlog/test_sync_command.py -q`
- Result: failed as expected before implementation
  - `test_map_fields_preserves_unrelated_custom_mapping_sections`
  - `test_map_fields_fails_safe_when_custom_mapping_file_is_invalid`
  - `test_sync_force_overwrite_external_baseline_creates_backup`

## Passing Evidence

- `2026-04-24T23:36:12+02:00`
- Command:
  `hatch run pytest tests/unit/specfact_backlog/test_map_fields_command.py tests/unit/specfact_backlog/test_sync_command.py -q`
- Result: passed

- `2026-04-24T23:36:12+02:00`
- Command:
  `hatch run pytest tests/unit/specfact_backlog -q`
- Result: passed (`74 passed`)

- `2026-04-24T23:58:55+02:00`
- Command:
  `hatch run python scripts/sign-modules.py --allow-unsigned --payload-from-filesystem packages/specfact-backlog/module-package.yaml`
- Result: passed after bumping `packages/specfact-backlog/module-package.yaml` from `0.41.17` to `0.41.18`

- `2026-04-24T23:58:55+02:00`
- Command:
  `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`
- Result: passed (`Verified 6 module manifest(s).`)

- `2026-04-24T23:58:55+02:00`
- Command:
  `hatch run contract-test`
- Result: passed (`654 passed`)

- `2026-04-24T23:58:55+02:00`
- Command:
  `hatch run smart-test`
- Result: passed (`654 passed`)

## Code Review

- `2026-04-24T23:58:55+02:00`
- Command:
  `hatch run specfact code review run --json --out .specfact/code-review.json --scope full`
- Result: completed with existing repository baseline debt (`1022 findings`, `418 blocking`) across multiple unrelated bundles and long-lived backlog surfaces

- `2026-04-24T23:58:55+02:00`
- Command:
  `hatch run specfact code review run --json --out .specfact/code-review.changed.json --scope changed`
- Result: completed with pre-existing findings on already-large backlog command surfaces (`178 findings`, `39 blocking`), primarily longstanding complexity/KISS/contract issues in `packages/specfact-backlog/src/specfact_backlog/backlog/commands.py`

### Review exception

The review gate was executed as required, but the reports are dominated by pre-existing repository and backlog-bundle debt unrelated to this narrow safe-write change. No new change-specific runtime regression was identified after the targeted tests, package tests, `contract-test`, and `smart-test` all passed. Full remediation of the review findings would require a separate cleanup/refactor change for existing backlog command complexity and contract coverage.
