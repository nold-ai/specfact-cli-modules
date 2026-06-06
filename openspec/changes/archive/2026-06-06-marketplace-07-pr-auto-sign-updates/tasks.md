# Tasks: marketplace-07-pr-auto-sign-updates

## 1. Specs and failing evidence

- [x] 1.1 Update the CI signing specs to require same-repo PR auto-sign remediation on every
  `pull_request` update to `dev` or `main`, and to scope `sign-modules-on-approval.yml` back to
  approval-only triggering.
- [x] 1.2 Add workflow tests for PR auto-sign remediation in
  `tests/unit/workflows/test_sign_modules_hardening.py` and trigger expectations in
  `tests/unit/workflows/test_sign_modules_on_approval.py`.
- [x] 1.3 Run the focused workflow tests and record the failing-before output in
  `openspec/changes/marketplace-07-pr-auto-sign-updates/TDD_EVIDENCE.md`.

## 2. Workflow implementation

- [x] 2.1 Update `.github/workflows/sign-modules.yml` so same-repo `pull_request` events targeting
  `dev` or `main` auto-sign changed manifests with CI secrets, commit
  `chore(modules): ci sign changed modules`, and push back to the PR head branch.
- [x] 2.2 Ensure the PR auto-sign path skips fork PRs and self-triggered bot commits while still
  allowing later human `synchronize` pushes to be re-signed automatically.
- [x] 2.3 Update `.github/workflows/sign-modules-on-approval.yml` so it triggers only on
  `pull_request_review`.

## 3. Verification and evidence

- [x] 3.1 Re-run the focused workflow tests after the workflow edits and confirm they pass.
- [x] 3.2 Run `hatch run yaml-lint` on the touched workflow files.
- [x] 3.3 Record the passing-after evidence in
  `openspec/changes/marketplace-07-pr-auto-sign-updates/TDD_EVIDENCE.md`.
