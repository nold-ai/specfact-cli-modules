# TDD Evidence: ci-02-codeql-cache-scope-isolation

## Failing-before

### 2026-08-28 Europe/Berlin — runtime compatibility correction

Before editing the manifest or workflow implementation:

```bash
hatch run pytest \
  tests/unit/workflows/test_pr_orchestrator_signing.py::test_pr_orchestrator_pins_exact_core_schema_smoke \
  tests/unit/workflows/test_pr_orchestrator_signing.py::test_pr_orchestrator_rejects_pep440_local_core_alias \
  tests/e2e/specfact_code_review/test_review_run_e2e.py::test_core_0_55_1_runtime_loads_schema_1_6_consumer_matrix \
  -q -p no:cacheprovider
```

Result: 3 failed. The workflow still exposed an exact-only compatibility job
and `===0.55.1`; the runtime E2E observed installed paired core 0.55.2 and the
manifest rejected it. A broader focused command also exposed an unrelated stale
local Hatch import (`specfact_cli.common`); the isolated red run above avoids
misclassifying that environment failure as compatibility evidence.

### 2026-08-27 Europe/Berlin

Before any workflow edit:

```bash
hatch run pytest \
  tests/unit/workflows/test_paired_core_ref_trust.py \
  tests/unit/workflows/test_requirements_evidence_workflow.py \
  tests/unit/test_check_docs_commands_script.py \
  -q -p no:cacheprovider
```

Result: 2 failed, 22 passed. The focused trust-boundary tests failed because
all three mixed-trust workflows still declared `workflow_dispatch`, retained
manual-only checkout paths, and guarded the dynamic checkout with an event
condition that GitHub's job-level cache analysis does not treat as isolation.

## Passing-after

### 2026-08-28 Europe/Berlin — runtime compatibility correction

- The focused compatibility suite passed: 15 passed, including the manifest
  minimum/no-upper-bound contracts, the complete workflow contract file, and
  schema 1.6 runtime loading under installed paired core 0.55.2.
- `openspec validate ci-02-codeql-cache-scope-isolation --strict` passed.
- `python scripts/publish_module.py --bundle specfact-code-review` passed for
  candidate version 0.49.60 and intentionally reviewed `>=0.55.1` metadata.
- Filesystem module checksum/version verification passed for all seven modules
  with the repository-supported missing-local-public-key allowance.
- YAML/registry validation and `actionlint` passed.
- The staged Requirements Evidence gate passed at planned maturity with all
  compatibility requirements mapped to unique collected pytest selectors.
- `./scripts/pre-commit-quality-checks.sh all` passed both blocks, including
  generated-command parity, documentation accountability, staged Requirements
  Evidence, changed-line review enforcement, and 28 contract tests.
- Format, type-check, lint, bundle-import, and contract gates passed. The
  contract suite selected 28 tests and all passed.
- `hatch run smart-test` and `hatch run test` each reached 1,646 passing tests
  with the same pre-existing platform-bound capsule failure on macOS/Python
  3.14: `test_capsule_runtime_loads_the_packaged_signed_lock_before_materialization`.
  The protected Linux/Python 3.11–3.13 workflow owns that capsule proof; all
  compatibility tests passed locally under paired core 0.55.2.
- A fresh independent post-patch review found an archive-ordering ambiguity and
  a missing 0.49.60 changelog entry. The compatibility spec now explicitly
  supersedes C14 exact-only release-snapshot wording without mutating its frozen
  checkpoint, the archive task preserves that precedence, and the changelog
  documents the installer-boundary correction.
- The changed-scope bug-hunt completed with exit 0 and no blocking findings.
  Its 20 advisories are explicitly excepted as unchanged legacy findings in the
  two long pre-existing test modules plus a local CrossHair environment missing
  pytest; none intersects the added compatibility assertions. The clean-code
  categories show no changed-line regression.

### 2026-08-27 Europe/Berlin

- The focused workflow suite passed: 24 passed.
- `actionlint` passed for the three modified workflows.
- `hatch run yaml-lint` passed and validated all seven manifests plus
  `registry/index.json`.
- `openspec validate ci-02-codeql-cache-scope-isolation --strict` passed.
- The changed path list contains only the three workflow files, one focused
  test, and this OpenSpec change. Module packages, manifests, registry data,
  dependency files, signatures, and release artifacts are unchanged.

### 2026-08-28 Europe/Berlin

- `hatch run format` passed; 1,223 files were unchanged.
- `hatch run type-check` passed with no errors, warnings, or notes.
- `hatch run lint` passed with a 10.00/10 score and no errors.
- `hatch run check-bundle-imports` passed.
- The strict filesystem signature command could not resolve local public keys.
  The repository-supported fallback,
  `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump --allow-missing-public-key`,
  passed for all seven modules. No signed assets or manifests changed.
- `hatch run contract-test` passed: 28 passed, 1,617 deselected.
- The staged requirements-evidence gate passed at planned maturity after mapping
  both the removed manual-run requirement and its replacement to unique focused
  test selectors.
- `hatch run smart-test` and `hatch run test` each reached 1,643 passing tests
  and the same two environment-bound failures. The first was caused by the
  sibling checkout exposing `specfact-cli` 0.54 instead of the required
  0.55.1; after installing the published 0.55.1 package in the isolated Hatch
  environment, the exact-core compatibility test passed. The second requires
  the repository's supported Linux/Python 3.11-3.13 capsule runtime, which is
  unavailable on this macOS/Python 3.14 host and is delegated to PR CI.
- The final changed-scope SpecFact bug-hunt review passed with
  `overall_verdict: PASS`, exit code 0, and zero findings. Its isolated
  CrossHair environment initially lacked PyYAML; loading PyYAML lazily through
  `importlib` kept semantic YAML parsing while allowing every review tool to
  complete without warnings.
- An independent bypass/regression review identified two issues: an
  archive-incompatible OpenSpec requirement rename and a substring-based YAML
  assertion. The delta now expresses an explicit removal plus addition, and
  the test parses trigger keys semantically with `yaml.BaseLoader`.
