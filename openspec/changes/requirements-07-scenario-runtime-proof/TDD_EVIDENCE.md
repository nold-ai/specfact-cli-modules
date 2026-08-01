# TDD Evidence: Requirements Scenario Runtime Proof

## Failing-before lifecycle contract

- **Recorded:** 2026-08-01 (Europe/Berlin)
- **Command:** `hatch run pytest tests/unit/specfact_requirements/test_requirements_lifecycle.py -q`
- **Result:** failed during collection as expected.
- **Failure:** `ModuleNotFoundError: No module named 'specfact_requirements.requirements.lifecycle'`
- **Intent:** establish the new lifecycle contract before production code:
  proposal readiness without execution claims, digest-bound acceptance, and
  exact JUnit reconciliation for red and final proof.

## Failing-before public CLI contract

- **Recorded:** 2026-08-01 (Europe/Berlin)
- **Command:** `hatch run pytest tests/integration/specfact_requirements/test_command_apps.py::test_requirements_evidence_exposes_lifecycle_options_and_reconciliation -q`
- **Result:** failed as expected.
- **Failure:** `--required-maturity` was absent from `specfact requirements evidence --help`.
- **Intent:** establish that the lifecycle contract is publicly reachable and
  that reconciliation remains a separate, non-executing operation.

## Passing lifecycle evidence

- **Recorded:** 2026-08-02 (Europe/Berlin)
- **Command:** `hatch run pytest tests/unit/workflows/test_requirements_evidence_workflow.py::test_requirements_evidence_workflow_runs_module_adapter_with_paired_core tests/unit/specfact_requirements/test_requirements_lifecycle.py tests/integration/specfact_requirements/test_command_apps.py::test_requirements_evidence_exposes_lifecycle_options_and_reconciliation -q`
- **Result:** 7 passed.
- **Command:** `PYTHONPATH=packages/specfact-project/src:packages/specfact-requirements/src hatch run python scripts/requirements_evidence_gate.py --repo-root . --base-ref origin/dev --required-maturity planned --output /private/tmp/requirements-r07-report.json --summary /private/tmp/requirements-r07-report.md`
- **Result:** passed with `delivery_status: proposal-only` and
  `implementation_evidence: not-yet-available`.
- **Proof:** lifecycle mappings are explicit from proposal time; a passing
  readiness decision neither claims execution nor weakens failing-first or
  final verification requirements.

## Review-remediation regression evidence

- **Recorded:** 2026-08-02 (Europe/Berlin)
- **Command:** `hatch run pytest tests/unit/specfact_requirements/test_requirements_lifecycle.py tests/integration/specfact_requirements/test_command_apps.py tests/unit/specfact_requirements/test_requirements_evidence.py -q`
- **Result:** 25 passed.
- **Proof:** ANSI-styled CLI help is checked semantically, unsafe selectors and
  unsafe or oversized JUnit are rejected, and only a complete passing
  `test-authored` plan can enter reconciliation.
