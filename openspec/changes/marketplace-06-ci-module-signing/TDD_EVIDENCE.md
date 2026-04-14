# TDD evidence: marketplace-06-ci-module-signing

Chain: delta specs (`ci-integration`, `ci-module-signing-on-approval`) → workflow tests → **Red** evidence →
implement `.github/workflows/sign-modules-on-approval.yml` + `pr-orchestrator.yml` → **Green** evidence.

## Red (workflow tests before `sign-modules-on-approval.yml` existed)

Artifacts: `tests/unit/workflows/test_sign_modules_on_approval.py` (expects
`.github/workflows/sign-modules-on-approval.yml`), and companion tests for
`pr-orchestrator.yml` / pre-commit parity added in the same change.

Captured **2026-04-14** by temporarily moving the workflow file aside and running one failing test:

```bash
python -m pytest \
  tests/unit/workflows/test_sign_modules_on_approval.py::test_sign_modules_on_approval_trigger_and_job_filter \
  -q
```

Excerpt (failure: missing `sign-modules-on-approval.yml`):

```text
tests/unit/workflows/test_sign_modules_on_approval.py F                  [100%]

=================================== FAILURES ===================================
_____________ test_sign_modules_on_approval_trigger_and_job_filter _____________

    def test_sign_modules_on_approval_trigger_and_job_filter() -> None:
>       workflow = _workflow_text()
...
E       FileNotFoundError: [Errno 2] No such file or directory: '.../.github/workflows/sign-modules-on-approval.yml'

=========================== short test summary info ============================
FAILED tests/unit/workflows/test_sign_modules_on_approval.py::test_sign_modules_on_approval_trigger_and_job_filter
============================== 1 failed in 0.22s ===============================
```

## Green (verification)

Run from worktree `feature/marketplace-06-ci-module-signing` (repo root of this change):

```bash
python -m pytest tests/unit/workflows/ tests/unit/test_pre_commit_quality_parity.py \
  tests/unit/test_pre_commit_verify_modules_signature_script.py -q
# workflow + pre-commit parity tests (2026-04-14)

hatch run contract-test
# 555 passed (2026-04-14, after sign-modules-on-approval hardening)

hatch run lint
# All checks passed

hatch run yaml-lint
# Validated manifests / registry

actionlint .github/workflows/pr-orchestrator.yml .github/workflows/sign-modules-on-approval.yml
# exit 0
```

### PR review follow-up (sign-modules-on-approval)

- Same-repo PRs only: job `if` adds `github.event.pull_request.head.repo.full_name == github.repository` so fork PRs are not pushed to the wrong remote.
- Checkout uses `head.ref` (branch tip) to align with `git push origin "HEAD:${PR_HEAD_REF}"`.
- Signing uses `MERGE_BASE="$(git merge-base HEAD "origin/${PR_BASE_REF}")"` after `git fetch origin "${PR_BASE_REF}" --no-tags` so `--changed-only` is PR-scoped vs the merge-base, not the moving base-branch tip.

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

## PR

- Opened: [specfact-cli-modules#188](https://github.com/nold-ai/specfact-cli-modules/pull/188) (target `dev`).

## Cleanup (post-merge, human)

Tasks 6.3–6.4 (remove worktree / branch after merge, record cleanup): pending merge.
