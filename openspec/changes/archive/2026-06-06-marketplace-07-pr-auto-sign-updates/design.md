# Design: Auto-Sign Module Manifest Updates On Every PR Sync

## Context

The repository already has two related workflows:

1. `sign-modules.yml` verifies module manifest integrity on `pull_request`, `push`, and
   `workflow_dispatch`. It also auto-signs pushes to protected `dev` and `main`, but it does not
   auto-sign PR branches.
2. `sign-modules-on-approval.yml` signs PR branches after trusted approval. Its recent
   `pull_request` path made later approved `synchronize` events eligible for signing, which created
   overlap and a self-trigger risk.

The requested behavior is broader than approval-time remediation: every same-repo PR update against
`dev` or `main` should repair checksums and signatures automatically so repeated review-fix pushes
stay mergeable without manual signing.

## Goals

- Auto-sign changed manifests on every same-repo PR update to `dev` or `main`.
- Keep fork PRs read-only.
- Avoid self-triggered signing loops from bot commits.
- Preserve existing push-to-`dev`/`main` signing behavior.

## Non-Goals

- Signing fork PRs.
- Changing publish or registry workflows.
- Removing approval-time signing as a workflow entry point if it can remain a harmless backstop.

## Decisions

### Decision 1: PR remediation belongs in `sign-modules.yml`

`sign-modules.yml` already runs on every relevant `pull_request` event. It is the correct place to
repair manifest integrity before verification because the same workflow can sign and then verify the
updated checkout in one run.

Implementation shape:

- checkout the PR head SHA for `pull_request` events
- sign changed manifests for same-repo PRs
- commit and push directly back to `github.event.pull_request.head.ref`
- run the existing verify step against the now-updated checkout

### Decision 2: Skip bot-authored self-sign commits

The PR remediation step must skip events triggered by the workflow's own commit. The guard is based
on the bot actor and the fixed commit message:

- actor: `github-actions[bot]`
- commit message: `chore(modules): ci sign changed modules`

That preserves repeated human review-fix pushes while preventing infinite self-sign loops.

### Decision 3: `sign-modules-on-approval.yml` returns to review-only triggering

Once PR-update remediation is handled in `sign-modules.yml`, the approval workflow no longer needs a
`pull_request` trigger. Keeping only `pull_request_review` avoids duplicate responsibility and keeps
the approval workflow aligned with its name.

## Risks / Trade-offs

- **Risk: detached checkout cannot push the PR branch**
  Mitigation: check out `github.event.pull_request.head.sha` and push with
  `git push origin "HEAD:${PR_HEAD_REF}"`.
- **Risk: stale verification after the signing push**
  Mitigation: sign before verify in the same job so the working tree already contains the updated
  manifests when verification runs.
- **Risk: duplicate signing between workflows**
  Mitigation: remove the `pull_request` trigger from `sign-modules-on-approval.yml`.

## Verification Plan

- Add workflow-structure tests for PR auto-sign steps and approval-only triggers.
- Capture a failing-before test run for the new expectations.
- Re-run focused workflow tests and YAML lint after implementation.
