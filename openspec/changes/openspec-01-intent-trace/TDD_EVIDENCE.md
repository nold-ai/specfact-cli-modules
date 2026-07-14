# TDD Evidence: openspec-01-intent-trace

## Failing-before

- Date: 2026-07-14 (Europe/Berlin)
- Command:

  ```bash
  hatch run test tests/unit/specfact_requirements/test_requirements_runtime.py tests/integration/specfact_requirements/test_command_apps.py
  ```

- Result: failed during collection, as expected before runtime implementation.
- Evidence: `ImportError: cannot import name 'import_openspec_change_to_bundle' from 'specfact_requirements.requirements.runtime'`.

The new tests cover OpenSpec and Spec Kit import delegation, read-only source
behavior, no partial persistence for core `unsupported-source-schema`,
layered-profile delegation, core gate-count presentation, and CLI explicit and
auto-detected OpenSpec sources.

## Passing-after

- Date: 2026-07-14 (Europe/Berlin)
- Command:

  ```bash
  hatch run pytest tests/unit/specfact_requirements/test_requirements_runtime.py tests/integration/specfact_requirements/test_command_apps.py -q
  ```

- Result: `17 passed`.
- The passing suite proves core-delegated OpenSpec and Spec Kit imports,
  read-only source handling, fail-closed schema rejection without a sidecar,
  layered-profile delegation, core gate-count presentation, and command-level
  explicit and auto-detected OpenSpec import behavior.

## Final quality gates

- `hatch run type-check -- packages/specfact-requirements/src tests/unit/specfact_requirements tests/integration/specfact_requirements` — passed with 0 errors.
- `hatch run lint` — passed.
- `hatch run yaml-lint` — passed.
- `hatch run check-bundle-imports` — passed.
- `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump --allow-missing-public-key` — passed for all manifests.
- `hatch run contract-test` — passed (28 tests).
- `hatch run smart-test` — passed (878 tests).
- `hatch run test` — passed (878 tests, 2 third-party deprecation warnings).
- `hatch run specfact code review run --enforcement changed --bug-hunt --json --out .specfact/code-review.json` — passed with exit code 0.
