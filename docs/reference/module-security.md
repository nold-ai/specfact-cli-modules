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
  - **Strict** (signatures required): `--require-signature --enforce-version-bump --payload-from-filesystem` (and optional `--version-check-base <git-ref>` in CI), same idea as the **specfact-cli** docs for `verify-modules-signature.py`.
  - **`--metadata-only`**: validates manifest shape (`integrity.checksum` format; optional `integrity.signature` presence when `--require-signature`) **without** hashing the bundle or verifying crypto — for **local pre-commit** on non-`main` branches only. **CI** (`.github/workflows/pr-orchestrator.yml`) always runs the **full** verifier without `--metadata-only`.
- **Pre-commit** (this repo): `scripts/pre-commit-verify-modules-signature.sh` follows the same **`require` / `omit`** policy shape as **specfact-cli** `scripts/pre-commit-verify-modules.sh`, driven by `scripts/git-branch-module-signature-flag.sh`. Here, `omit` maps to `--metadata-only` so developers are not forced to re-sign locally; **specfact-cli** `omit` still runs **full checksum** verification against paths under `modules/` / `src/specfact_cli/modules/`.
  - `--version-check-base <git-ref>` is used for PR comparisons in CI.
- **CI signing**: Approved same-repo PRs to `dev` or `main` may receive automated signing commits via `sign-modules-on-approval.yml` (repository secrets; merge-base scoped `--changed-only`).

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
