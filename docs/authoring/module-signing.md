---
layout: default
title: Module Signing and Key Rotation
permalink: /authoring/module-signing/
redirect_from:
  - /guides/module-signing-and-key-rotation/
description: Runbook for signing bundled modules, placing public keys, rotating keys, and revoking compromised keys.
keywords: [signing, security, verification, trust, modules]
audience: [solo, team, enterprise]
expertise_level: [advanced]
---

# Module Signing and Key Rotation

This runbook defines the repeatable process for signing bundled modules and verifying signatures in SpecFact CLI.

## Key Placement

Repository/public key path used by CLI verification:

- `resources/keys/module-signing-public.pem` (repository source path)

Runtime key resolution order:

1. Explicit key argument (internal verifier calls)
2. `SPECFACT_MODULE_PUBLIC_KEY_PEM`
3. Bundled key file at `resources/keys/module-signing-public.pem` (source) or `specfact_cli/resources/keys/module-signing-public.pem` (installed package)

Never store private signing keys in the repository.

## Generate Keys

Ed25519 (recommended):

```bash
openssl genpkey -algorithm ED25519 -out module-signing-private.pem
openssl pkey -in module-signing-private.pem -pubout -out module-signing-public.pem
```

RSA 4096 (supported):

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out module-signing-private.pem
openssl pkey -in module-signing-private.pem -pubout -out module-signing-public.pem
```

## Sign Bundled Modules

Preferred (strict, with private key):

- **Key file**: `--key-file <path>` or set `SPECFACT_MODULE_PRIVATE_SIGN_KEY_FILE` (or legacy `SPECFACT_MODULE_SIGNING_PRIVATE_KEY_FILE`).
- **Inline PEM**: Set `SPECFACT_MODULE_PRIVATE_SIGN_KEY` (or legacy `SPECFACT_MODULE_SIGNING_PRIVATE_KEY_PEM`) to the PEM string; no file needed. Useful in CI where the key is in a secret.
- **Payload mode**: Use `--payload-from-filesystem` so the payload matches verify and publish tarball excludes (`.git`, `tests`, cache dirs).

```bash
KEY_FILE="${SPECFACT_MODULE_PRIVATE_SIGN_KEY_FILE:-.specfact/sign-keys/module-signing-private.pem}"
python scripts/sign-modules.py --key-file "$KEY_FILE" --payload-from-filesystem packages/*/module-package.yaml
```

Encrypted private key options:

```bash
# Prompt interactively for passphrase (TTY)
python scripts/sign-modules.py --key-file "$KEY_FILE" --payload-from-filesystem packages/specfact-backlog/module-package.yaml

# Explicit passphrase flag (avoid shell history when possible)
python scripts/sign-modules.py --key-file "$KEY_FILE" --payload-from-filesystem --passphrase '***' packages/specfact-backlog/module-package.yaml

# Passphrase over stdin (CI-safe pattern)
printf '%s' "$SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE" | \
  python scripts/sign-modules.py --key-file "$KEY_FILE" --payload-from-filesystem --passphrase-stdin packages/specfact-backlog/module-package.yaml
```

Versioning guard:

- The signer enforces module version increments for changed module contents.
- If module files changed and version is unchanged, signing fails until version is bumped.
- Override exists for exceptional local workflows: `--allow-same-version` (not recommended).
- Module versions are independent from CLI package version; bump only modules whose payload changed.

Changed-modules automation (recommended for release prep):

```bash
# Bump changed modules by patch and sign only those modules
hatch run python scripts/sign-modules.py \
  --key-file "$KEY_FILE" \
  --payload-from-filesystem \
  --changed-only \
  --base-ref origin/dev \
  --bump-version patch

# Verify after signing (must match sign payload mode). This matches dev-targeting CI: checksum +
# version policy only—dev CI omits --require-signature:
hatch run python scripts/verify-modules-signature.py --payload-from-filesystem --enforce-version-bump --version-check-base origin/dev

# Main-equivalent (strict) verification: dev CI does not run this, but use it locally when you want
# cryptographic signatures enforced like on main. Same verifier flags as above, plus
# --require-signature. Example with --version-check-base origin/dev (typical feature → dev PR);
# before merging to main, point --version-check-base at origin/main so version policy matches the
# integration target:
hatch run python scripts/verify-modules-signature.py --require-signature --payload-from-filesystem --enforce-version-bump --version-check-base origin/dev
hatch run python scripts/verify-modules-signature.py --require-signature --payload-from-filesystem --enforce-version-bump --version-check-base origin/main
```

Wrapper for single manifest:

```bash
bash scripts/sign-module.sh --key-file "$KEY_FILE" packages/specfact-backlog/module-package.yaml
# stdin passphrase:
printf '%s' "$SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE" | \
  bash scripts/sign-module.sh --key-file "$KEY_FILE" --passphrase-stdin packages/specfact-backlog/module-package.yaml
```

Local test-only unsigned mode:

```bash
python scripts/sign-modules.py --allow-unsigned --payload-from-filesystem packages/specfact-backlog/module-package.yaml
```

## Verify Signatures Locally

Checksum + version enforcement (matches **`dev`** / feature CI and pre-commit when not on `main`):

```bash
python scripts/verify-modules-signature.py --payload-from-filesystem --enforce-version-bump
```

Strict verification (checksum + **signature** required, matches **`main`** CI):

```bash
python scripts/verify-modules-signature.py --require-signature --payload-from-filesystem --enforce-version-bump
```

With explicit public key file:

```bash
python scripts/verify-modules-signature.py --require-signature --payload-from-filesystem --enforce-version-bump --public-key-file resources/keys/module-signing-public.pem
```

## CI Enforcement

`pr-orchestrator.yml` job **`verify-module-signatures`** always runs with `--payload-from-filesystem --enforce-version-bump`. It adds **`--require-signature` only when the pull request or push targets `main`**. For **`dev`** and feature work, the job still enforces checksums and version bumps so unsigned manifests can land on `dev`; signatures are expected by the time changes reach **`main`**.

### Signing on approval (same-repo PRs)

Workflow **`sign-modules-on-approval.yml`** runs when a review is **submitted** and **approved** on a PR whose base is **`dev`** or **`main`**, and only when the PR head is in **this** repository (`head.repo` equals the base repo). It checks out **`github.event.pull_request.head.sha`** (the commit that was approved, not the moving branch tip), uses `SPECFACT_MODULE_PRIVATE_SIGN_KEY` and `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE` (each validated with a named error if missing), discovers changes against the **merge-base** with the base branch (not the moving base tip alone), runs `scripts/sign-modules.py --changed-only --bump-version patch --payload-from-filesystem`, and commits results **without** `[skip ci]` so PR checks and downstream workflows run on the signed head. If `git push` is rejected because the PR branch advanced after approval, the job fails with guidance to update the branch and re-approve. **Fork PRs** are skipped (the default `GITHUB_TOKEN` cannot push to a contributor fork).

### Pre-commit

The first pre-commit hook runs **`scripts/pre-commit-verify-modules-signature.sh`**, which mirrors CI: **`--require-signature` on branch `main`**, or when **`GITHUB_BASE_REF=main`** in Actions pull-request contexts; otherwise the same baseline formal verify as PRs to **`dev`** (`--payload-from-filesystem --enforce-version-bump`, no **`--require-signature`**). On failure it runs **`sign-modules.py --allow-unsigned --payload-from-filesystem`** (`--changed-only` vs **`HEAD`**, then vs **`HEAD~1`** for manifests still failing), **`git add`** those `module-package.yaml` paths, and re-verifies. It does **not** rewrite **`registry/`** (publish workflows own signed artifacts and index updates). **`yaml-lint`** allows a semver **ahead** manifest vs **`registry/index.json`** until **`publish-modules`** reconciles.

## Rotation Procedure

1. Generate new keypair in secure environment.
2. Replace `resources/keys/module-signing-public.pem` with new public key.
3. Re-sign all bundled module manifests with the new private key.
4. Run verifier locally: `python scripts/verify-modules-signature.py --require-signature --payload-from-filesystem`.
5. Commit public key + re-signed manifests in one change.
6. Merge to `dev`, then `main` after CI passes.

## Revocation Procedure

If a private key is compromised:

1. Treat all signatures from that key as untrusted.
2. Generate new keypair immediately.
3. Replace public key file in repo.
4. Re-sign all bundled modules with new private key.
5. Merge emergency fix branch and invalidate prior release artifacts operationally.

Current limitation:

- Runtime key-revocation list support is not yet implemented.
- Revocation is currently handled by rotating the trusted public key and re-signing all bundled manifests.
