# TDD Evidence: ci-01-workflow-dispatch-core-ref-trust

## Failing-before

### 2026-08-23 Europe/Berlin

Before any workflow edit:

```bash
hatch run pytest tests/unit/workflows/test_paired_core_ref_trust.py \
  -q -p no:cacheprovider
```

Result: 6 failed as expected. All three dynamic resolver/checkout pairs lacked
the manual-event exclusion, and all three workflows lacked mutually exclusive
literal `main` and `dev` manual checkout paths.

## Passing-after

### 2026-08-23 Europe/Berlin

- The focused suite and the three pre-existing affected workflow suites passed:
  39 tests initially, then 35 after consolidating parameterized cases into two
  standard-library-only loop tests during review remediation.
- The dynamic resolver and checkout remain available for non-manual events.
- Manual `main` uses literal core `main`; every other manual ref uses literal
  core `dev`; all paired-core checkouts retain `persist-credentials: false`.
- `actionlint` passed for the three changed workflows.
- `hatch run yaml-lint` and strict OpenSpec validation passed.

## Final quality evidence

### 2026-08-23 Europe/Berlin

- `hatch run format`: 1,193 files unchanged.
- `hatch run lint`: passed with a 10.00/10 Pylint score.
- `hatch run type-check`: 0 errors, warnings, or notes.
- `hatch run contract-test`: 28 passed.
- `hatch run smart-test`: 1,567 passed and 2 pre-existing environment/C14
  tests failed. The local paired core is 0.54.0 while the immutable C14 smoke
  requires exactly 0.55.1; the other failure is the existing C14 signed-lock
  capsule materialization test. This change modifies no package or C14 path.
- After installing exact published core 0.55.1 in the disposable worktree
  environment, the immutable C14 schema smoke passed. The unrelated signed-lock
  capsule test remained failed with `capsule_runtime_unavailable:`.
- `hatch run check-bundle-imports` passed.
- Strict signature verification could not load local public keys for the seven
  unchanged manifests. The repository-approved
  `--allow-missing-public-key` payload checksum and version-bump verification
  passed for all seven manifests.
- The staged schema-v2 Requirements evidence gate passed at planned maturity.
- The first changed-scope SpecFact review reported one CrossHair environment
  warning because its isolated Python could not import `pytest`. The new test
  was rewritten to use only the standard library while retaining both contract
  assertions; the 35-test affected suite passed after that remediation.
- The changed-scope SpecFact review rerun under exact core 0.55.1 passed with
  zero findings, warnings, or advisories. CI remains pending.
