# TDD Evidence

## Failing Before

- `hatch run pytest tests/unit/test_dev_bootstrap.py tests/unit/test_local_bundle_source_alignment.py -q`
  - Result: FAIL before production edits (`2 failed, 11 passed`).
  - The new bootstrap and repository-guidance assertions could not find the required preservation language; both existing surfaces still prescribed a user-scope uninstall.

## Passing After

- `hatch run pytest tests/unit/test_dev_bootstrap.py tests/unit/test_local_bundle_source_alignment.py -q`
  - Result: PASS (`13 passed`).
  - The bootstrap and repository rule surfaces now preserve user-scoped installations, and the local import-isolation test remains green under its accurate in-memory eviction name.

## Quality Gates

- `hatch run format`: PASS (1,229 files unchanged).
- `hatch run type-check`: PASS (0 errors, 0 warnings).
- `hatch run lint`: PASS (Pylint 10.00/10).
- `hatch run yaml-lint`: PASS (seven manifests plus registry).
- `hatch run check-bundle-imports`: PASS.
- `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump --allow-missing-public-key`: PASS for all seven modules. No signed payload or manifest changed, so no module version bump is required. The strict local-key form was also attempted and stopped only because this worktree does not contain the public key.
- `hatch run contract-test`: PASS (`28 passed, 1753 deselected`).
- Staged Requirements evidence gate at maturity `planned`: PASS with schema-v2 mappings for all changed scenarios and exact pytest selectors.
- `hatch run smart-test`: reached the full suite with one failure in `test_capsule_runtime_loads_the_packaged_signed_lock_before_materialization`; the same failure reproduces from an isolated clean `origin/dev` worktree at `870fea3d`, so it is baseline C14/environment debt rather than a regression from this change.
- `hatch run test`: `1780 passed, 1 failed`; the only failure is the same clean-`origin/dev` capsule-runtime baseline failure.
- `hatch run specfact code review run --enforcement changed --bug-hunt --json --out .specfact/code-review.json`: PASS after replacing one changed-file `print(..., file=sys.stderr)` warning; the worktree review reported schema 1.4, score 120, zero findings, exit code 0.
- The staged commit-hook review exposed three whole-file Pylint warnings in pre-existing test helpers; they were refactored and the focused tests/lint reran green. Its remaining advisory is environment-only: the external CrossHair process cannot import `pytest` while inspecting the staged test module.
- `git diff --check`: PASS.
