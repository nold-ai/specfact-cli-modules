---
layout: default
title: Module Security
permalink: /reference/module-security/
description: Trust model, checksum and signature verification, and integrity lifecycle for module packages.
keywords: [module, security, trust, checksum, signature]
audience: [solo, team, enterprise]
expertise_level: [advanced]
---

# Module Security

Module packages carry **publisher** and **integrity** metadata so installation, bootstrap, and runtime discovery verify trust before enabling a module.

## Trust model

- **Manifest metadata**: `module-package.yaml` may include `publisher` (name, email, attributes) and `integrity` (checksum, optional signature).
- **Checksum verification**: Verification computes a deterministic hash of the full module payload (all module files, with manifest canonicalization that excludes `integrity` itself). Supported algorithms: `sha256`, `sha384`, `sha512` in `algo:hex` format.
- **Signature verification**: If `integrity.signature` is present and a public key is configured, signature validation proves provenance over the same full payload.
- **Publisher trust gate**: Non-official publishers require one-time explicit trust (interactive confirmation or `--trust-non-official` / `SPECFACT_TRUST_NON_OFFICIAL`).
- **Denylist gate**: Modules listed in denylist are blocked before install/bootstrap regardless of source.

## Integrity flow

1. Discovery reads `module-package.yaml` and parses `integrity.checksum`.
2. At install/bootstrap/verification time, the tool hashes the full module payload and compares it to `integrity.checksum`.
3. On mismatch, the module is skipped and a security warning is logged.
4. Other modules continue to register; one failing trust does not block the rest.

## Signing automation

- **Script**: `scripts/sign-module.sh` signs one or more `module-package.yaml` manifests.
- **Payload scope**: Signing covers all files under the module directory (not only the manifest).
- **Encrypted key support**: Passphrase can be provided with:
  - `--passphrase` (local only; avoid shell history in CI)
  - `--passphrase-stdin` (recommended for secure piping)
  - `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE`
- **Key sources**:
  - `--key-file`
  - `SPECFACT_MODULE_PRIVATE_SIGN_KEY` (PEM content)
  - `SPECFACT_MODULE_PRIVATE_SIGN_KEY_FILE`
- **Version guard**: Changed module contents must have a bumped module version before signing. Override exists only for controlled local cases via `--allow-same-version`.
- **Changed-only release mode**: `scripts/sign-modules.py --changed-only --base-ref <git-ref> --bump-version <patch|minor|major>` auto-selects modules with payload changes, bumps versions when unchanged, and signs only those modules.
- **Version decoupling**: module versions are semver-managed per module payload and do not need to track CLI package version.
- **CI secrets**:
  - `SPECFACT_MODULE_PRIVATE_SIGN_KEY`
  - `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE`
- **Verification command** (`scripts/verify-modules-signature.py`):
  - **Baseline (CI)**: `--payload-from-filesystem --enforce-version-bump` — full payload checksum verification plus version-bump enforcement.
  - **Dev-target PR mode**: `.github/workflows/pr-orchestrator.yml` uses the baseline verifier for pull requests targeting `dev` (full payload checksum + version bump, **no** `--require-signature`). Cryptographic signing is applied after merge via `sign-modules` / approval workflows, not required on the PR head.
  - **Strict mode**: add `--require-signature` so every manifest must include a verifiable `integrity.signature`. In `.github/workflows/pr-orchestrator.yml` this is appended for **pull requests whose base is `main`** and for **pushes to `main`**, in addition to the baseline flags. Locally, `scripts/pre-commit-verify-modules-signature.sh` adds `--require-signature` only when the checkout (or `GITHUB_BASE_REF` in Actions) is **`main`**.
  - **Local non-main hook mode**: `scripts/pre-commit-verify-modules-signature.sh` otherwise runs the same baseline flags as dev-target PR CI (no `--require-signature`). Refresh `integrity.checksum` without a private key using `scripts/sign-modules.py --allow-unsigned --payload-from-filesystem`.
  - **Pull request CI** also passes `--version-check-base <git-ref>` (typically `origin/<base branch>`) so version rules compare against the PR base.
  - **`--metadata-only`** remains available for optional tooling that only needs manifest shape and checksum **format** checks without hashing module trees.
- **CI signing**: Approved same-repo PRs to `dev` or `main` from trusted reviewer associations may receive automated signing commits via `sign-modules-on-approval.yml` (repository secrets; merge-base scoped `--changed-only`).

## Public key and key rotation

- Store trusted public key in:
  - `resources/keys/module-signing-public.pem`
- Optional fallback path:
  - `src/specfact_cli/resources/keys/module-signing-public.pem`
- Rotate keys by:
  1. generating a new key pair,
  2. updating trusted public key in repository,
  3. re-signing affected modules with incremented versions,
  4. running signature verification and version-bump checks in CI.

## Versioned dependencies

Manifest may declare versioned module and pip dependencies via `module_dependencies_versioned` and `pip_dependencies_versioned` (each entry: `name`, `version_specifier`). These are parsed and stored for installation-time resolution while keeping legacy `module_dependencies` / `pip_dependencies` lists backward compatible.
