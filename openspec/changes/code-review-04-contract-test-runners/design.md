# Design: Contract and TDD Gate Runners for `specfact-code-review`

## Target package paths

- `packages/specfact-code-review/src/specfact_code_review/tools/contract_runner.py`
- `packages/specfact-code-review/src/specfact_code_review/run/runner.py`
- `tests/unit/specfact_code_review/tools/test_contract_runner.py`
- `tests/unit/specfact_code_review/run/test_runner.py`

## `contract_runner.py`

### AST scan

Use Python's `ast` module to inspect supplied Python files.

For each public function definition:

1. Skip names starting with `_`
2. Check decorators for `require` or `ensure`
3. Emit `ReviewFinding(category="contracts", severity="warning",
   rule="MISSING_ICONTRACT")` when neither contract decorator is present

The runner should ignore functions outside the requested file list and degrade
gracefully on parse failures by returning a `tool_error` finding instead of raising.

### CrossHair fast pass

Run:

```python
cmd = ["crosshair", "check", "--per_path_timeout", "2", *paths]
```

Map counterexample output to `ReviewFinding(category="contracts",
severity="warning", tool="crosshair")`.

If CrossHair times out or is unavailable, continue returning AST-scan results and add a
`tool_error` finding only for unavailable/binary-execution failures.

## `runner.py`

The orchestrator composes already-available review runners in sequence:

1. Ruff
2. Radon
3. BasedPyright
4. Pylint
5. Contract runner
6. TDD gate, unless `no_tests=True`

It should merge findings from all invoked runners and then call the existing scorer to
build a `ReviewReport`.

## TDD gate design

For changed bundle files under
`packages/specfact-code-review/src/specfact_code_review/...`, derive the expected unit
test file under `tests/unit/specfact_code_review/...` using the module-relative path:

```python
rel = src_file.relative_to("packages/specfact-code-review/src")
expected = Path("tests/unit") / rel.parent / f"test_{rel.name}"
```

Rules:

- Missing expected test file -> `TEST_FILE_MISSING`, `category="testing"`,
  `severity="error"`
- Test failures -> testing finding with `severity="error"`
- Coverage below 80% -> testing finding with `severity="warning"`
- `no_tests=True` -> skip TDD gate entirely

The initial implementation should target changed bundle files only and may use the
existing smart-test commands plus parseable output to determine pass/fail and coverage.

## Dependency note

`runner.py` depends on bundle-local `basedpyright_runner` and `pylint_runner`. Those
surfaces are defined by `code-review-03-type-governance-runners` and must exist in this
repository before `code-review-04` implementation begins.
