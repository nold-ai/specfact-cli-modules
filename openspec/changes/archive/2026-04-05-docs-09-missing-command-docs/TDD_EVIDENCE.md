# TDD Evidence: docs-09-missing-command-docs

## Failing Evidence

### Missing command docs contract

Command:

```bash
HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run pytest tests/unit/docs/test_missing_command_docs.py -q
```

Initial result:

- Failed because the new command pages did not exist
- Failed because the bundle overview pages did not link to the new deep-dive docs

## Passing Evidence

### Missing command docs contract

Command:

```bash
HATCH_DATA_DIR=/tmp/hatch-data \
HATCH_CACHE_DIR=/tmp/hatch-cache \
VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata \
hatch run pytest tests/unit/docs/test_missing_command_docs.py -q
```

Result:

- Passed: `2 passed`

### Command help alignment spot checks

Command pattern:

```bash
PYTHONPATH=packages/specfact-spec/src:packages/specfact-govern/src:packages/specfact-code-review/src:packages/specfact-codebase/src \
.venv/bin/python
```

Result:

- Verified help/option surfaces for:
  - `specfact spec validate`
  - `specfact spec backward-compat`
  - `specfact spec generate-tests`
  - `specfact spec mock`
  - `specfact govern enforce stage`
  - `specfact govern enforce sdd`
  - `specfact govern patch apply`
  - `specfact code review run`
  - `specfact code review ledger {status,update,reset}`
  - `specfact code review rules {show,init,update}`
  - `specfact code analyze contracts`
  - `specfact code drift detect`
  - `specfact code repro`
  - `specfact code repro setup`

### Jekyll build

Command:

```bash
bundle exec jekyll build --destination ../_site
```

Result:

- Passed: build completed successfully in `1.416 seconds`
