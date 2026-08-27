# TDD Evidence: ci-02-codeql-cache-scope-isolation

## Failing-before

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
