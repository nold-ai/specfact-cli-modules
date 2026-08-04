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

## Failing-before Code Review Requirements-context remediation

- **Recorded:** 2026-08-04 (Europe/Berlin)
- **Command:** `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py::test_run_command_rejects_non_v2_requirements_evidence_before_review tests/unit/specfact_code_review/run/test_findings.py::test_review_report_uses_schema_1_5_for_requirements_evidence -q`
- **Result:** failed as expected (3 failures).
- **Failure:** schema-v1 and schema-v3 finalized-looking proof packets reached
  review execution, and a report containing Requirements provenance retained
  schema version `1.0`.
- **Intent:** establish the compatibility boundary before accepting only
  finalized schema-v2 provenance for core #662.

## Passing Code Review Requirements context

- **Recorded:** 2026-08-04 (Europe/Berlin)
- **Commands:**
  - `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py::test_run_command_retains_finalized_requirements_provenance_without_verdict_fusion tests/unit/specfact_code_review/run/test_commands.py::test_run_command_rejects_nonfinal_requirements_evidence_before_review tests/unit/specfact_code_review/run/test_commands.py::test_run_command_rejects_non_v2_requirements_evidence_before_review tests/unit/specfact_code_review/run/test_findings.py::test_review_report_uses_schema_1_5_for_requirements_evidence tests/unit/specfact_code_review/run/test_findings.py::test_review_report_accepts_legacy_schema_fixtures_without_requirements_provenance -q`
  - `openspec validate requirements-07-scenario-runtime-proof --strict`
- **Result:** focused regression and legacy-compatibility tests passed; strict
  OpenSpec validation passed.
- **Proof:** `specfact code review run --requirements-evidence <path>` accepts
  only a finalized schema-v2 proof, emits report schema `1.5` with its
  path/digests/source/verdict in review JSON, and does not use the Requirements
  verdict to calculate the review exit code or verdict.

## Review-remediation proof-completeness evidence

- **Recorded:** 2026-08-05 (Europe/Berlin)
- **Failing-before command:** `hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_commands.py tests/unit/scripts/test_generate_command_overview.py tests/unit/test_check_docs_commands_script.py`
- **Result:** 4 failed, 75 passed as expected.
- **Failures:** Code Review accepted a schema-v2 packet that lacked the
  submitted and execution plans, selectors, maturity, findings, and JUnit
  digest; the command inventory emitted `govern enforce` paths twice; and the
  docs checker accepted `specfact code import import`.
- **Passing-after command:** `hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_commands.py tests/unit/scripts/test_generate_command_overview.py tests/unit/test_check_docs_commands_script.py`
- **Result:** 79 passed.
- **Proof:** Code Review rejects incomplete final Requirements proof packets
  before review execution; published command records are unique; and docs
  validation rejects duplicated executable command tokens.
