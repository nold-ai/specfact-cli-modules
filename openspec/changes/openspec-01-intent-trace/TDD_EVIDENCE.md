# TDD Evidence: openspec-01-intent-trace

## Failing-before

- Date: 2026-07-14 (Europe/Berlin)
- Command:

  ```bash
  hatch run test tests/unit/specfact_requirements/test_requirements_runtime.py tests/integration/specfact_requirements/test_command_apps.py
  ```

- Result: failed during collection, as expected before runtime implementation.
- Evidence: `ImportError: cannot import name 'import_native_requirements_to_bundle' from 'specfact_requirements.requirements.runtime'`.

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

- Result: `21 passed`.
- The passing suite proves core-delegated OpenSpec and Spec Kit imports,
  read-only source handling, fail-closed schema rejection without a sidecar,
  layered-profile delegation, core gate-count presentation, and command-level
  explicit and auto-detected OpenSpec import behavior.

## Review-regression evidence

- Date: 2026-07-14 (Europe/Berlin)
- Command:

  ```bash
  hatch run pytest tests/unit/specfact_requirements/test_requirements_runtime.py tests/integration/specfact_requirements/test_command_apps.py -q
  ```

- Failing-before result: 4 failures. OpenSpec auto-detection treated
  `openspec/changes/archive/` as an import candidate; the CLI did not expose an
  optional positional source path; and a regular-file source raised a runtime
  contract violation instead of a CLI usage error.
- Passing-after result: `21 passed` after archive exclusion, typed optional
  source-path parsing, explicit Spec Kit CLI coverage, and generated-command
  metadata support were added.

## Code-review regression evidence

- Date: 2026-07-14 (Europe/Berlin)
- Command:

  ```bash
  hatch run pytest tests/unit/specfact_code_review/tools/test_radon_runner.py -q
  ```

- Failing-before result: `1 failed, 7 passed`; a Typer command without a
  `ctx` parameter still produced `kiss.parameter-count.warning`.
- Passing-after result: `8 passed`; decorated Typer commands are exempt from
  the parameter-count rule regardless of whether they accept a context.

## Final quality gates

- `hatch run type-check -- packages/specfact-requirements/src/specfact_requirements/requirements packages/specfact-code-review/src/specfact_code_review/tools/radon_runner.py tests/unit/specfact_requirements tests/integration/specfact_requirements/test_command_apps.py tests/unit/specfact_code_review/tools/test_radon_runner.py` — passed with 0 errors.
- `hatch run lint` — passed.
- `hatch run yaml-lint` — passed.
- `hatch run check-bundle-imports` — passed.
- `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump --allow-missing-public-key` — passed for all manifests.
- `hatch run contract-test` — passed (28 tests).
- `hatch run smart-test` — passed (883 tests).
- `hatch run test` — passed (883 tests, 2 third-party deprecation warnings).
- `openspec validate openspec-01-intent-trace --strict` — passed.
- `hatch run specfact code review run --enforcement changed --bug-hunt --json --out /private/tmp/specfact-code-review-final.json` — passed with no findings.
