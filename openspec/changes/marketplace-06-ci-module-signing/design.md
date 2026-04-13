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

3. **No pre-commit signing check**: The modules pre-commit (`scripts/pre-commit-quality-checks.sh`)
   does NOT include a module-signature verification step. No pre-commit changes are required.

Both repos share the same `scripts/sign-modules.py` logic (or a copy of it) and the same GitHub
secrets (`SPECFACT_MODULE_PRIVATE_SIGN_KEY`, `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE`), which
are already configured via `publish-modules.yml`.

## Goals / Non-Goals

**Goals:**
- Add automated CI signing on PR approval, covering `packages/*/module-package.yaml` manifests.
- Relax `verify-module-signatures` in `pr-orchestrator.yml` for dev-targeting events.
- Enable non-interactive development on feature/dev branches without a local private key.

**Non-Goals:**
- Adding a pre-commit signature verification step (none exists today; introducing one would
  recreate the problem).
- Adding a `sign-modules.yml` hardening workflow (out of scope; this repo's release flow differs
  from specfact-cli).
- Changing `publish-modules.yml` or the registry index logic.
- Changing install-time signature verification for end users.

## Decisions

### Decision 1: Reuse `scripts/sign-modules.py` with `--changed-only` and packages root

**Chosen**: Run `sign-modules.py --changed-only --base-ref "origin/<base>" --bump-version patch
--payload-from-filesystem` from the repo root. The script's `_iter_manifests()` discovers
manifests under `src/specfact_cli/modules/` and `modules/`; for this repo those directories are
absent, so `--changed-only` must be combined with explicit manifest discovery or the script
patched to also check `packages/`.

**Approach**: Pass manifests explicitly by discovering them in the workflow step:
```bash
mapfile -t MANIFESTS < <(find packages -name 'module-package.yaml' -type f | sort)
python scripts/sign-modules.py "${MANIFESTS[@]}"
```
Use `--allow-same-version` is NOT used; `--bump-version patch` auto-bumps version when unchanged
from base ref (same policy as specfact-cli).

**Alternative**: Patch `sign-modules.py` `_iter_manifests()` to also scan `packages/`. Rejected
for this change — keeping the script unchanged reduces diff surface; the explicit discovery in the
workflow is transparent.

### Decision 2: Same trigger as specfact-cli (`pull_request_review`, approved)

All design decisions from `specfact-cli/marketplace-06-ci-module-signing` Design § Decisions 1–5
apply identically. See that document for rationale. The key difference is the manifest discovery
path (`packages/` vs `src/specfact_cli/modules/` + `modules/`).

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
