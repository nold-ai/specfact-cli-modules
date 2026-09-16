# Native aggregate coverage policy controller evidence

Date: 2026-09-16 (Europe/Berlin).

The three ordinary-customer pytest execution scenarios were added to the canonical portable-runtime specification before the regression tests. The controller tests serialize a target observation and provide the actual subprocess exit through a controlled subprocess boundary; they exercise the real controller, observation validator, and coverage evaluator. These are controller regressions, not a Linux capsule acceptance run.

## Recorded failure

Command: `source /private/tmp/specfact-475-module-env.sh` then `.venv/bin/pytest tests/unit/specfact_code_review/run/test_portable_worker.py -q`.

Before implementation: **21 failed, 50 passed**, 1.44 seconds. Full assertion transcript: [PR478_NATIVE_COVERAGE_POLICY_RED.txt](PR478_NATIVE_COVERAGE_POLICY_RED.txt).

Failing cases cover native aggregate policy failures despite passing tests, coexistence with failed test outcomes and incomplete collection (including no records), malformed scalar fields and missing receipt fields, contradictory native modes and exit zero. Passing controls preserve older observations without the new field and non-failing native, reviewer, and disabled receipts for both zero and unexplained nonzero exits.

## Passing evidence

After implementation, the same focused command: **71 passed**, 0.23 seconds (Python 3.14.7, pytest 9.1.1). Local full output: `/private/tmp/specfact-478-native-coverage-policy-green.txt`.

Ruff formatting/checks and focused BasedPyright: PASS (zero type errors or warnings). New private helper complexity is at most 9. Focused Pylint retains only the preexisting deferred runner import and native pytest `_ensure_unconfigure` protected-access warnings; the relevant import AST and test function AST are unchanged from HEAD. Existing `run_portable_pytest` and `validate_observation` complexities remain 11 and 12 respectively. No new warning exception was added.

## Behavior and limits

`TEST_COVERAGE_POLICY_FAILED` is a blocking testing finding only when a validated native receipt records a measured total, a native threshold failure, and actual pytest exit 1. The message retains the actual total, threshold, and precision. Existing test findings and incomplete execution diagnostics remain visible. Invalid receipts produce `project_pytest_coverage_policy_invalid`; absent receipts retain the existing reader behavior. The controller validates bounded scalar types but does not recreate Coverage rounding or infer a failure from an arbitrary exit 1. Per-file policy and native configured thresholds are unchanged.

The target producer and native Coverage lifecycle are validated separately by the integration owner. Linux signed-capsule confirmation and combined source gates remain pending; this evidence does not claim those passed.

## Specific target coverage diagnostic follow-up

The existing scenarios require exact disabled, unsupported, and missing-worker evidence reasons. Before the follow-up production edit, new controller regressions produced **8 failed, 75 passed** (0.29 seconds); their transcript is appended to the same RED artifact. After implementation, the focused file has **83 passed** (0.26 seconds). Ruff format/check and focused BasedPyright passed; Pylint retains only the same two baseline warnings.

When coverage files are absent, the controller now retains a nonempty target `coverage_diagnostic` exactly. A present non-string diagnostic yields `project_pytest_coverage_diagnostic_invalid`; absent/empty diagnostics preserve the existing `project_pytest_coverage_missing` remedy. Collection/internal errors keep precedence, and actual failed test records plus native aggregate policy findings remain visible. This does not change collection, execution, source coverage thresholds, or native outcomes.
