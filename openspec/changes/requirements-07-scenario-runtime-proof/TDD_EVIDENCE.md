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
