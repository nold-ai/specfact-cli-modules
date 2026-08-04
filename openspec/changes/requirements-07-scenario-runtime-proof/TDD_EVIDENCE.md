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

## Failing-before legacy TDD ledger migration

- **Recorded:** 2026-08-04 (Europe/Berlin)
- **Command:** `hatch run pytest tests/unit/specfact_requirements/test_requirements_lifecycle.py::test_final_reconciliation_records_a_matching_legacy_tdd_ledger -q`
- **Result:** failed as expected (1 failure).
- **Failure:** `reconcile_junit()` did not accept an explicit
  `legacy_tdd_evidence` record, so a previously recorded TDD-first ledger
  could not serve as a transparent one-time migration basis.
- **Intent:** preserve strict red-JUnit enforcement for normal delivery while
  making legacy evidence visibly distinct from red proof.

## Passing-after legacy TDD ledger migration

- **Recorded:** 2026-08-04 (Europe/Berlin)
- **Command:** `hatch run pytest tests/unit/specfact_requirements/test_requirements_lifecycle.py tests/integration/specfact_requirements/test_command_apps.py::test_requirements_evidence_exposes_lifecycle_options_and_reconciliation -q`
- **Result:** 15 passed.
- **Proof:** final reconciliation accepts only a matching, explicit ledger
  record; stale records, ambiguous proof bases, and red-stage ledger use do
  not waive the normal red-proof requirement. A successful migration reports
  `implementation_evidence: passing-after-legacy-tdd-ledger` rather than
  claiming JUnit red proof.

## Final migration quality evidence

- **Recorded:** 2026-08-04 (Europe/Berlin)
- **Commands:** `hatch run format`, `hatch run type-check`, `hatch run lint`,
  `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run
  contract-test`, `hatch run smart-test`, `openspec validate
  requirements-07-scenario-runtime-proof --strict`, and `hatch run specfact
  code review run --enforcement changed --bug-hunt --json --out
  .specfact/code-review.json`.
- **Result:** format, type, lint, YAML, bundle-import, contract, smart-test,
  and strict OpenSpec validation passed. The final changed-scope review has no
  blocking findings.
- **Reviewed advisory:** the remaining informational AI-bloat suggestion is on
  the pre-existing `evidence_command` orchestration. It is outside this
  migration's behavioral change; collapsing it would mix an unrelated
  readability refactor into a release-critical provenance fix. It is retained
  intentionally and does not change the reviewed reconciliation surface.
