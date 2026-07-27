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

## PR #365 review remediation

- **2026-07-27 (Europe/Berlin) failing-before:** `hatch run pytest
  tests/unit/scripts/test_requirements_evidence_fallback.py
  tests/unit/specfact_requirements/test_requirements_evidence.py
  tests/unit/scripts/test_requirements_evidence_gate.py
  tests/unit/docs/test_llms_overview_freshness.py -q` reported the expected
  rollback-after-publication, aliased-output, and manifest-registry metadata
  drift failures. It also exposed the duplicated requirements-05 source and
  stale generated command overview already present after the `main` to `dev`
  merge.
- **Remediation:** the fallback restores both artifacts after JSON publication
  fails, public evidence rejects aliased output paths before evaluation, and
  command overview validation compares official identity, version, install
  artifact, ownership, dependency, description, and compatibility metadata.
  The duplicate active requirements-05 change was archived with `openspec
  archive --skip-specs`; the stale duplicate archive was removed, retaining
  the canonical 2026-07-26 archive. Generated command-overview artifacts were
  refreshed against the current paired core command tree.
- **2026-07-27 (Europe/Berlin) passing-after:** `hatch run pytest
  tests/unit/scripts/test_requirements_evidence_fallback.py
  tests/unit/specfact_requirements/test_requirements_evidence.py
  tests/unit/scripts/test_requirements_evidence_gate.py
  tests/unit/docs/test_llms_overview_freshness.py::test_command_overview_rejects_official_manifest_registry_metadata_drift -q`
  reported `29 passed`; `openspec validate requirements-06-evidence-enforcement
  --strict` passed.

## PR #366 review remediation

- **2026-07-28 (Europe/Berlin) failing-before:** `hatch run pytest
  tests/unit/specfact_requirements/test_requirements_evidence.py
  tests/integration/specfact_requirements/test_command_apps.py
  tests/unit/scripts/test_requirements_evidence_fallback.py
  tests/unit/docs/test_llms_overview_freshness.py -q` reported six expected
  failures: hard-linked report destinations were not rejected, the public CLI
  exposed a raw destination error, first-replacement rollback was incomplete,
  rollback could mask publication failure, and release version/artifact drift
  was accepted.
- **2026-07-28 (Europe/Berlin) passing-after:** the same command reported
  `35 passed in 1.67s`; `openspec validate requirements-06-evidence-enforcement
  --strict` passed. Coverage includes existing hard-link aliases, actionable
  CLI errors, rollback after either replacement and rollback failure, newer
  registry-version rejection, immutable artifact validation, and permitted
  manifest-newer `dev` publication state.
- **Quality evidence (2026-07-28, Europe/Berlin):** full `hatch run test`
  reported `929 passed`; required format, type, lint, YAML, bundle-import,
  command-overview, contract, and smart-test gates passed. The refreshed
  `0.3.3` requirements manifest checksum passed filesystem verification under
  the dev-target unsigned policy. `hatch run specfact code review run
  --enforcement changed --bug-hunt --json --out .specfact/code-review.json`
  completed with `PASS`, score `115`, and no findings.
