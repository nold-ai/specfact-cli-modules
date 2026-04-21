# TDD Evidence: marketplace-07-pr-auto-sign-updates

## Failing Before

Date: 2026-04-21

Command:

```bash
python3 -m pytest tests/unit/workflows/test_sign_modules_hardening.py tests/unit/workflows/test_sign_modules_on_approval.py -q
```

Result:

```text
collected 16 items

tests/unit/workflows/test_sign_modules_hardening.py ....FF....
tests/unit/workflows/test_sign_modules_on_approval.py F.....

FAILED tests/unit/workflows/test_sign_modules_hardening.py::test_sign_modules_hardening_auto_signs_same_repo_pull_requests
FAILED tests/unit/workflows/test_sign_modules_hardening.py::test_sign_modules_hardening_checks_out_pr_head_for_pr_events
FAILED tests/unit/workflows/test_sign_modules_on_approval.py::test_sign_modules_on_approval_trigger_and_job_filter
```

Interpretation:

- `sign-modules.yml` did not yet auto-sign same-repo PR updates.
- `sign-modules.yml` did not yet check out the PR head SHA for pull-request remediation.
- `sign-modules-on-approval.yml` still had a `pull_request` trigger instead of approval-only
  triggering.

## Passing After

Date: 2026-04-21

Command:

```bash
python3 -m pytest tests/unit/workflows/test_sign_modules_hardening.py tests/unit/workflows/test_sign_modules_on_approval.py -q
```

Result:

```text
collected 16 items

tests/unit/workflows/test_sign_modules_hardening.py ..........
tests/unit/workflows/test_sign_modules_on_approval.py ......

16 passed in 0.33s
```

Additional verification:

```bash
hatch run yaml-lint .github/workflows/sign-modules.yml .github/workflows/sign-modules-on-approval.yml
openspec validate marketplace-07-pr-auto-sign-updates --strict
hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json \
  .github/workflows/sign-modules.yml \
  .github/workflows/sign-modules-on-approval.yml \
  tests/unit/workflows/test_sign_modules_hardening.py \
  tests/unit/workflows/test_sign_modules_on_approval.py \
  openspec/changes/marketplace-07-pr-auto-sign-updates/proposal.md \
  openspec/changes/marketplace-07-pr-auto-sign-updates/design.md \
  openspec/changes/marketplace-07-pr-auto-sign-updates/tasks.md \
  openspec/changes/marketplace-07-pr-auto-sign-updates/specs/ci-integration/spec.md \
  openspec/changes/marketplace-07-pr-auto-sign-updates/specs/ci-module-signing-on-approval/spec.md \
  openspec/specs/ci-integration/spec.md \
  openspec/specs/ci-module-signing-on-approval/spec.md
```

Observed outcomes:

- `yaml-lint`: passed (`Validated 6 manifests and registry/index.json`)
- `openspec validate marketplace-07-pr-auto-sign-updates --strict`: passed
- SpecFact code review: `Review completed with no findings.`
