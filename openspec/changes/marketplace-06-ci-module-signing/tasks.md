## 1. Branch, coordination, and issue sync

- [ ] 1.1 Create `feature/marketplace-06-ci-module-signing` in a dedicated worktree from `origin/dev`;
  run pre-flight status checks.
- [ ] 1.2 ~~Create a GitHub User Story issue~~ Issue created: [specfact-cli-modules#185](https://github.com/nold-ai/specfact-cli-modules/issues/185); `proposal.md` Source Tracking updated. Paired core issue: [specfact-cli#500](https://github.com/nold-ai/specfact-cli/issues/500). *(done)*
- [ ] 1.3 Confirm `SPECFACT_MODULE_PRIVATE_SIGN_KEY` and `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE`
  are set as repository secrets in `specfact-cli-modules` (should already be present via
  publish-modules.yml). *(human)*

## 2. Specs and TDD evidence (failing tests first)

- [ ] 2.1 Write tests for the updated `pr-orchestrator.yml` `verify-module-signatures` logic in
  `tests/unit/workflows/test_pr_orchestrator_signing.py` — confirm branch split: dev PRs pass
  without `--require-signature`, main PRs enforce it. Capture failing output in `TDD_EVIDENCE.md`.
- [ ] 2.2 Write workflow-structure tests for `sign-modules-on-approval.yml` in
  `tests/unit/workflows/test_sign_modules_on_approval.py` — validate trigger config, manifest
  discovery from `packages/`, and commit-back step. Capture failing output in `TDD_EVIDENCE.md`.

## 3. pr-orchestrator.yml — split verify by target branch

- [ ] 3.1 In `.github/workflows/pr-orchestrator.yml`, in the `verify-module-signatures` job,
  extract the target branch from `github.event.pull_request.base.ref` (PR events) and `github.ref`
  (push events).
- [ ] 3.2 For events targeting `dev`: run `verify-modules-signature.py` without `--require-signature`
  (keep `--payload-from-filesystem --enforce-version-bump` and any `--version-check-base`).
- [ ] 3.3 For events targeting `main`: retain `--require-signature --payload-from-filesystem
  --enforce-version-bump` with `--version-check-base`.
- [ ] 3.4 Run actionlint on the modified workflow and fix any findings.

## 4. New workflow — sign-modules-on-approval.yml

- [ ] 4.1 Create `.github/workflows/sign-modules-on-approval.yml` with trigger:
  `pull_request_review: types: [submitted]`.
- [ ] 4.2 Add job condition:
  `if: github.event.review.state == 'approved' && (github.event.pull_request.base.ref == 'dev' || github.event.pull_request.base.ref == 'main')`.
- [ ] 4.3 Add steps: checkout PR head, set up Python 3.12, install signing deps
  (`pyyaml beartype icontract cryptography cffi`).
- [ ] 4.4 Add manifest discovery step:
  `mapfile -t MANIFESTS < <(find packages -name 'module-package.yaml' -type f | sort)`.
- [ ] 4.5 Add signing step: compute `BASE_REF="origin/${{ github.event.pull_request.base.ref }}"`;
  for each changed manifest (compare against BASE_REF), run
  `python scripts/sign-modules.py --allow-same-version --payload-from-filesystem "<manifest>"`;
  or use `--changed-only --base-ref "$BASE_REF"` if the script supports `packages/` discovery.
  Fail immediately if `SPECFACT_MODULE_PRIVATE_SIGN_KEY` or `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE`
  is empty.
- [ ] 4.6 Add write-back step: configure git user (github-actions bot), `git add` changed manifests,
  commit `chore(modules): ci sign changed modules [skip ci]` (skip if no changes), push using
  `GITHUB_TOKEN` with `permissions: contents: write`.
- [ ] 4.7 Add job summary step showing which manifests were signed or "no changes detected".
- [ ] 4.8 Run actionlint on the new workflow. Fix any findings.

## 5. Testing and quality gates

- [ ] 5.1 Run the new tests from 2.1–2.2 and confirm they pass after the workflow changes.
- [ ] 5.2 Run `hatch run lint` (or equivalent) to confirm no regressions.
- [ ] 5.3 Run `hatch run yaml-lint` to validate all modified and new YAML workflow files.
- [ ] 5.4 Run `specfact code review run --json --out .specfact/code-review.json`; resolve every
  finding at warning or error severity.
- [ ] 5.5 Record final passing test runs in `TDD_EVIDENCE.md`.

## 6. PR and cleanup

- [ ] 6.1 Push the branch and open a PR targeting `dev`; verify CI passes (dev PRs no longer
  require `--require-signature`).
- [ ] 6.2 Link the PR to the GitHub issue created in 1.2 and to the paired specfact-cli PR.
- [ ] 6.3 After merge: remove the worktree, delete the local branch, run `git worktree prune`.
- [ ] 6.4 Record cleanup completion in `TDD_EVIDENCE.md`.
