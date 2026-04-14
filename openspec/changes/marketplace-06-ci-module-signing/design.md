# Design: CI-Driven Module Signing On PR Approval (specfact-cli-modules)

## Context

This repo differs from `specfact-cli` in two important ways that shape the implementation:

1. **Module manifest location**: Manifests live under `packages/*/module-package.yaml`, not
   `src/specfact_cli/modules/` or `modules/`. The signing script (`scripts/sign-modules.py`) must
   be invoked with the correct root discovery path, or with explicit manifest paths.

2. **No existing signing workflow**: `specfact-cli` has a `sign-modules.yml` hardening workflow
   that already scopes verification to dev/main; this repo has no equivalent. Only
   `pr-orchestrator.yml` has a `verify-module-signatures` job, and it always runs
   `--require-signature` regardless of target branch.

3. **Pre-commit verify hook**: `.pre-commit-config.yaml` already runs `verify-modules-signature.py` on
   every commit. That entry is replaced with a thin wrapper that mirrors `pr-orchestrator` policy
   (`--require-signature` when the current branch is `main`, or `GITHUB_BASE_REF` is `main` in Actions).
   Block 1 quality stages in `pre-commit-quality-checks.sh` are unchanged.

Both repos share the same `scripts/sign-modules.py` logic (or a copy of it) and the same GitHub
secrets (`SPECFACT_MODULE_PRIVATE_SIGN_KEY`, `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE`), which
are already configured via `publish-modules.yml`.

## Goals / Non-Goals

**Goals:**
- Add automated CI signing on PR approval, covering `packages/*/module-package.yaml` manifests.
- Relax `verify-module-signatures` in `pr-orchestrator.yml` for dev-targeting events.
- Enable non-interactive development on feature/dev branches without a local private key.

**Non-Goals:**
- Adding *new* mandatory local signing with a private key (the wrapper relaxes `--require-signature`
  off `main` instead).
- Adding a `sign-modules.yml` hardening workflow (out of scope; this repo's release flow differs
  from specfact-cli).
- Changing `publish-modules.yml` or the registry index logic.
- Changing install-time signature verification for end users.

## Decisions

### Decision 1: Reuse `scripts/sign-modules.py` with `--changed-only` and merge-base

**Chosen**: In CI, `git fetch origin <base>`, compute `MERGE_BASE="$(git merge-base HEAD "origin/<base>")"`,
then run `sign-modules.py --changed-only --base-ref "$MERGE_BASE" --bump-version patch
--payload-from-filesystem` with **no explicit manifest arguments** so the script selects changed
modules itself. `_iter_manifests()` discovers `packages/*/module-package.yaml` (this repo layout).

**Approach** (workflow sign step):

```bash
git fetch origin "${PR_BASE_REF}" --no-tags
MERGE_BASE="$(git merge-base HEAD "origin/${PR_BASE_REF}")"
python scripts/sign-modules.py \
  --changed-only \
  --base-ref "$MERGE_BASE" \
  --bump-version patch \
  --payload-from-filesystem
```

`--allow-same-version` is not used; `--bump-version patch` auto-bumps when the version is unchanged
from the comparison ref (same policy as specfact-cli).

A separate workflow step may still **count** manifests under `packages/` for job summary only; it
does not feed paths into `sign-modules.py`.

### Decision 2: Same trigger as specfact-cli (`pull_request_review`, approved)

All design decisions from `specfact-cli/marketplace-06-ci-module-signing` Design § Decisions 1–5
apply identically. See that document for rationale. This repo’s `sign-modules.py` discovers manifests
under `packages/`; merge-base scoping for `--changed-only` matches PR-local changes.

### Decision 3: pr-orchestrator split mirrors specfact-cli exactly

The `verify-module-signatures` job split (dev: no `--require-signature`; main:
`--require-signature`) is identical in logic to the specfact-cli change. The only structural
difference is that this workflow uses `SPECFACT_MODULE_PUBLIC_SIGN_KEY` for verification (the
public key secret); the signing job uses the private key secret.

## Risks / Trade-offs

- **Risk: `_iter_manifests()` in sign-modules.py doesn't discover `packages/`** — mitigated by
  explicit manifest discovery in the workflow step (see Decision 1).
- **Risk: Version bump race condition** — if two PRs to dev are approved simultaneously and both
  change the same module, auto-bump produces the same patch version. Mitigation: signing is
  idempotent; the second approval re-signs but the version bump check compares against
  `origin/dev`, which may already include the first bump. In practice this scenario is unlikely
  given the single-maintainer cadence; a future change can add mutex locking if needed.
- All other risks from the paired `specfact-cli` design apply equally here.

## Migration Plan

Identical to `specfact-cli/marketplace-06-ci-module-signing` Migration Plan. Merge on `dev` first
(no `--require-signature` on dev PRs), then the signing workflow activates automatically for the
next main-targeting PR.

## Open Questions

Same open questions as the paired specfact-cli change (GPG-signed bot commits, dev registry
endpoint). No modules-specific open questions.
