# TDD Evidence: code-review-10 review scope modes

## Failing

### 2026-03-17 `tests/unit/specfact_code_review/run/test_commands.py`

Command:

```bash
HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run pytest tests/unit/specfact_code_review/run/test_commands.py -q
```

Result: `5 failed, 14 passed`

Key failures before implementation:

- `test_run_command_supports_full_scope_and_path_filters`
  - exit code was `2` because `--scope` was not supported yet
- `test_run_command_supports_changed_scope_with_repeatable_path_filters`
  - exit code was `2` because `--scope`/`--path` were not supported yet
- `test_run_command_rejects_scope_mixed_with_positional_files`
  - CLI returned the generic option error instead of the governed mixed-targeting message
- `test_run_command_rejects_path_mixed_with_positional_files`
  - CLI returned the generic option error instead of the governed mixed-targeting message
- `test_run_command_fails_when_scope_and_paths_match_no_files`
  - CLI returned the generic option error instead of an actionable empty-scope failure

## Passing

### 2026-03-17 Focused scope-mode tests

Commands:

```bash
HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/run/test_runner.py -q

HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run pytest tests/e2e/specfact_code_review/test_review_run_e2e.py -q

HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run validate-cli-contracts
```

Results:

- `tests/unit/specfact_code_review/run/test_commands.py` and `tests/unit/specfact_code_review/run/test_runner.py`: `36 passed`
- `tests/e2e/specfact_code_review/test_review_run_e2e.py`: `2 passed`
- CLI contract validation: `Validated 3 CLI contract scenario files.`

### 2026-03-17 SpecFact dogfood review

Command:

```bash
SPECFACT_ALLOW_UNSIGNED=1 \
HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run specfact code review run \
  --scope changed \
  --path packages/specfact-code-review \
  --path tests/unit/specfact_code_review \
  --json \
  --out /tmp/code-review-10-report.json
```

Result:

- verdict: `PASS`
- score: `115`
- findings: `0`

### 2026-03-17 Worktree quality gates

Commands completed successfully:

```bash
HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run format
HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run type-check
HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run lint
HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run check-bundle-imports
HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run smart-test
HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run contract-test
```

Results:

- `type-check`: `0 errors, 0 warnings, 0 notes`
- `lint`: `10.00/10`
- `smart-test`: `383 passed`
- `contract-test`: `384 passed`

Pending:

- `verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`
  - blocked until the final `packages/specfact-code-review/module-package.yaml` changes in this worktree are re-signed
