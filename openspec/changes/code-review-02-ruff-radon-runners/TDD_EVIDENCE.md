# TDD Evidence: code-review-02-ruff-radon-runners

## Failing test evidence

Command:

```bash
SPECFACT_CLI_REPO="$HOME/specfact-cli" hatch run test -- tests/unit/specfact_code_review/tools/test_ruff_runner.py tests/unit/specfact_code_review/tools/test_radon_runner.py -v
```

Observed failure:

```text
ImportError while importing test module '/workspace/tests/unit/specfact_code_review/tools/test_radon_runner.py'
E   ModuleNotFoundError: No module named 'specfact_code_review.tools'

ImportError while importing test module '/workspace/tests/unit/specfact_code_review/tools/test_ruff_runner.py'
E   ModuleNotFoundError: No module named 'specfact_code_review.tools'
```

## Passing test evidence

Command:

```bash
SPECFACT_CLI_REPO="$HOME/specfact-cli" hatch run python -m pytest tests/unit/specfact_code_review/tools -v
```

Observed pass:

```text
tests/unit/specfact_code_review/tools/test_radon_runner.py::test_run_radon_maps_complexity_thresholds_and_filters_files PASSED
tests/unit/specfact_code_review/tools/test_radon_runner.py::test_run_radon_returns_no_findings_for_complexity_twelve_or_below PASSED
tests/unit/specfact_code_review/tools/test_radon_runner.py::test_run_radon_returns_tool_error_on_parse_error PASSED
tests/unit/specfact_code_review/tools/test_ruff_runner.py::test_run_ruff_maps_categories_and_fixable_flag PASSED
tests/unit/specfact_code_review/tools/test_ruff_runner.py::test_run_ruff_filters_findings_to_requested_files PASSED
tests/unit/specfact_code_review/tools/test_ruff_runner.py::test_run_ruff_returns_tool_error_on_parse_error PASSED
tests/unit/specfact_code_review/tools/test_ruff_runner.py::test_run_ruff_returns_tool_error_when_ruff_is_unavailable PASSED

============================== 7 passed in 0.20s ===============================
```

## Review regression evidence

Command:

```bash
hatch run python -m pytest tests/unit/specfact_code_review/tools/test_ruff_runner.py tests/unit/specfact_code_review/tools/test_radon_runner.py -v
```

Observed pass:

```text
tests/unit/specfact_code_review/tools/test_radon_runner.py::test_run_radon_maps_complexity_thresholds_and_filters_files PASSED
tests/unit/specfact_code_review/tools/test_radon_runner.py::test_run_radon_returns_no_findings_for_complexity_twelve_or_below PASSED
tests/unit/specfact_code_review/tools/test_radon_runner.py::test_run_radon_returns_tool_error_on_parse_error PASSED
tests/unit/specfact_code_review/tools/test_ruff_runner.py::test_run_ruff_maps_categories_and_fixable_flag PASSED
tests/unit/specfact_code_review/tools/test_ruff_runner.py::test_run_ruff_filters_findings_to_requested_files PASSED
tests/unit/specfact_code_review/tools/test_ruff_runner.py::test_run_ruff_skips_unsupported_rule_families PASSED
tests/unit/specfact_code_review/tools/test_ruff_runner.py::test_run_ruff_returns_tool_error_on_parse_error PASSED
tests/unit/specfact_code_review/tools/test_ruff_runner.py::test_run_ruff_returns_tool_error_when_ruff_is_unavailable PASSED

============================== 8 passed in 0.21s ===============================
```
