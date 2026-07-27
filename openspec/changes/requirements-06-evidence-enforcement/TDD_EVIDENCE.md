# TDD Evidence — requirements-06-evidence-enforcement

## Failing before implementation

- **2026-07-27 (Europe/Berlin)** — `hatch run pytest
  tests/integration/specfact_requirements/test_command_apps.py
  tests/unit/specfact_requirements/test_requirements_evidence.py
  tests/unit/workflows/test_requirements_evidence_workflow.py
  tests/unit/test_pre_commit_quality_parity.py -q`
- **Result:** failed during collection because
  `specfact_requirements.requirements.runtime` did not expose
  `_materialize_git_index_snapshot`; the new reusable evaluator and staged
  selection mode did not exist.

## Passing after implementation

- **2026-07-27 (Europe/Berlin)** — `hatch run pytest
  tests/integration/specfact_requirements/test_command_apps.py::test_requirements_evidence_requires_exactly_one_source_selection_mode
  tests/unit/specfact_requirements/test_requirements_evidence.py
  tests/unit/scripts/test_requirements_evidence_gate.py
  tests/unit/workflows/test_requirements_evidence_workflow.py
  tests/unit/test_pre_commit_quality_parity.py -q`
- **Result:** `29 passed in 0.60s`.
- **Coverage:** mutually exclusive source selection, immutable staged-index
  snapshots, archived source stability, report persistence, public-command CI
  use, and pre-commit ordering.

## Final verification

- **2026-07-27 (Europe/Berlin)** — `hatch run pytest
  tests/integration/specfact_requirements/test_command_apps.py -q`
- **Result:** `11 passed in 0.86s` against `specfact-cli 0.53.5`, including
  native Spec Kit readiness rejection without bundle persistence.
- **2026-07-27 (Europe/Berlin)** — `hatch run smart-test`
- **Result:** passed.
- **Additional gates:** `format`, `type-check`, `lint`, `yaml-lint`,
  `check-bundle-imports`, `check-command-overview`, `check-command-contract`,
  `contract-test`, strict OpenSpec validation, module signature/version
  verification, and changed-line SpecFact code review passed.
- **Staged evidence:** `PYTHONPATH=packages/specfact-requirements/src hatch run
  python scripts/requirements_evidence_gate.py --staged ...` passed after the
  change-local `requirements-evidence.yaml` mapped both imported requirements
  to their unit, integration, hook, and workflow test evidence.
