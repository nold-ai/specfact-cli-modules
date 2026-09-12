# Customer pytest execution evidence

Date: 2026-09-13, Europe/Berlin. Scope: the existing requirement that required
analyzers actually execute on an independent customer repository; local evidence
retains its existing assurance class.

## Observed failure

Hosted candidate run `34723950359` reported `targeted-pytest-coverage` as passing
for an independent calculator fixture. Inspection established that the local
capsule request did not provide the complete pytest inventory. The legacy TDD
selector recognizes the modules repository's source layout and returned no
findings without executing the customer's tests.

The dedicated regression file
`tests/unit/specfact_code_review/run/test_customer_pytest_execution.py` failed
four cases before implementation: default and configured customer test layouts
received `complete_pytest_inventory=False`; empty and unsupported inventories
incorrectly reported PASS. Log: `/private/tmp/capsule-customer-pytest-red.log`.

Four subsequent assertions failed because analyzer evidence omitted the runtime
ABI (`environment_id`). Log: `/private/tmp/capsule-customer-pytest-abi-red.log`.
A child-startup regression then failed because pytest launched with plain `-c`
and lacked authenticated import roots before importing pytest. Log:
`/private/tmp/capsule-customer-pytest-child-red.log`.

## Repair

Local capsule execution now resolves repository pytest and coverage policy,
plans complete selectors using the existing capability checks, and mounts the
projected configuration with private output paths. Unsupported or empty test
inventories remain UNKNOWN with a failing exit. Explicit `no_tests` keeps its
existing recorded skip behavior and cannot satisfy the customer gate.

Capsule pytest children use isolated, no-site startup, trusted analyzer, builtin
and project-runtime roots before pytest imports, and no ambient PYTHONPATH.
Snapshot imports are appended after those roots. Host compatibility is unchanged.
Runtime `environment_id` accompanies launched analyzer evidence, local
inventory failures and early acquisition failures without altering diagnostic
reason strings. The acquisition regression also failed before this change; log:
`/private/tmp/capsule-customer-pytest-acquisition-red.log`. One legacy sandbox test fixture now creates an actual test
and uses its temporary repository as the working directory.

## Passing checks and remaining acceptance

Command:

```sh
SPECFACT_CLI_REPO=/private/tmp/specfact-core-customer-466 hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_customer_pytest_execution.py tests/unit/specfact_code_review/run/test_runner.py --tb=short
```

Result: **410 passed in 12.85 seconds** on macOS, Python 3.14.7; the capsule
boundary is mocked in these unit regressions. Ruff checks and formatting passed
for the touched Python files; BasedPyright reported zero errors and warnings for
`runner.py`. Log: `/private/tmp/capsule-customer-pytest-green.log`.

Actual non-root analyzer and pytest execution on all three supported Linux ABIs
remains a hosted customer-matrix gate; these unit results do not satisfy it.
Project suites needing unsupported pytest hooks or unattested dependencies still
fail closed. A declared, supported repository test selection may exercise the
modules repository without claiming coverage of its complete test suite.

## Shared-worktree enforcement fixture isolation

The combined suite recorded an unexpected UNKNOWN in
`test_capsule_review_changed_enforcement_preserves_fail_without_changed_line_evidence`
(`/private/tmp/capsule-tests-final-466.log`); the same test passed immediately
in isolation before any change. Its original fixture reviewed from the actively
edited repository, allowing real worktree identity checks to observe unrelated
concurrent edits. Such drift is correctly rejected by production code. Concurrent
worktree mutation is the likely cause; the original failure did not retain its
analyzer diagnostic, so that specific race is not independently proven.

The enforcement-only fixture now creates a real selected file under `tmp_path`
and reviews from that isolated directory. Production identity checks are
unchanged. Verification: **46 changed-enforcement tests passed in 7.49 seconds**,
with 358 unrelated cases deselected; log:
`/private/tmp/capsule-enforcement-fixture-466.log`.

## CLI contract tests explicitly select their test runner

Hosted run `34723950399` failed the two host-tool CLI fixture tests and three
JSON report contract cases on Python 3.11, 3.12 and 3.13. Their implicit
`SPECFACT_CODE_REVIEW_DEV_HOST_COMPAT` setup previously relied on an acquisition
cache miss. With working acquisition, those tests instead reached real Linux
materialization and failed with
`bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. The failure is
recorded in `/private/tmp/capsule-old-quality-466.log`; these suites assert CLI
format, selection and host-analyzer outcomes rather than namespace prerequisites.

Those cases now explicitly request the non-autouse
`host_analyzer_cli_contract` fixture. The fixture injects the host review runner
at the CLI boundary and rejects any accidental capsule acquisition. Only the
named tests opt in. No production fallback, analyzer permission, or customer
matrix behavior changes; namespace and capsule acceptance remain mandatory in
the dedicated customer gate.

The same hosted run's minimum-core smoke failed earlier, at its equality check
between the current lock and the historical completed C14 checkpoint. The
workflow owner is correcting that separate check to authenticate the current
module lock binding while preserving the historical checkpoint.

Targeted validation after test isolation: **7 passed in 33.36 seconds**, with
Ruff, formatting and diff whitespace checks passing. Command:

```sh
SPECFACT_CLI_REPO=/private/tmp/specfact-core-customer-466 hatch run python -m pytest -q tests/e2e/specfact_code_review/test_review_run_e2e.py tests/integration/specfact_code_review/test_cli_contract_review_run_reports.py --tb=short
```

Log: `/private/tmp/capsule-cli-contract-isolation-466.log`.
