# TDD evidence: marketplace-06-ci-module-signing

## Red (workflow tests before implementation)

Not captured in this session: `sign-modules-on-approval.yml` did not exist until implementation, so
`tests/unit/workflows/test_sign_modules_on_approval.py` would fail on missing file. After adding the
workflow and updating `pr-orchestrator.yml`, tests were turned green.

## Green (verification)

Run from worktree `feature/marketplace-06-ci-module-signing` (repo root of this change):

```bash
python -m pytest tests/unit/workflows/ -q
# 7 passed (2026-04-14)

hatch run lint
# All checks passed

hatch run yaml-lint
# Validated manifests / registry

actionlint .github/workflows/pr-orchestrator.yml .github/workflows/sign-modules-on-approval.yml
# exit 0
```

SpecFact code review (use Hatch so `semgrep` resolves to the project venv; system `specfact` may
invoke a broken `semgrep` shim):

```bash
hatch run specfact code review run --json --out .specfact/code-review.json --include-tests \
  tests/unit/workflows/test_pr_orchestrator_signing.py \
  tests/unit/workflows/test_sign_modules_on_approval.py
# exit 0 (2026-04-14)
```

## Pre-commit note

`scripts/pre_commit_code_review.py` now skips `openspec/changes/**/*.md` (including `tasks.md`) so
the SpecFact review gate does not parse Markdown task lists as Python (false positives).

## PR / cleanup (post-merge, human)

Tasks 6.1–6.4 (push PR, link issues, worktree cleanup after merge): not executed in this session.
