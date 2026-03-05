---
layout: default
title: Publishing Modules
permalink: /guides/publishing-modules/
description: Package and publish SpecFact modules to a registry (tarball, checksum, optional signing).
---

# Publishing modules

This guide describes how SpecFact modules are validated and published into this repository's registry (`registry/index.json`, `registry/modules/`, `registry/signatures/`).

## Module structure

Your module must have:

- A directory containing `module-package.yaml` (the manifest).
- Manifest fields: `name`, `version`, `commands` (required). For marketplace distribution, use `namespace/name` (e.g. `acme-corp/backlog-pro`) and optional `publisher`, `tier`.

Recommended layout:

```text
<module-dir>/
  module-package.yaml
  src/
    __init__.py
    commands.py   # or app.py, etc.
```

Exclude from the package: `.git`, `__pycache__`, `tests`, `.pytest_cache`, `*.pyc`, `*.pyo`.

## Script: publish-module.py

Use `scripts/publish-module.py` as a publish pre-check (monotonic version and manifest/registry consistency):

```bash
python scripts/publish-module.py --bundle specfact-backlog
python scripts/publish-module.py --bundle backlog
```

The script validates:

- target bundle exists under `packages/`
- manifest version is valid
- manifest version is greater than current `registry/index.json` `latest_version`
- `core_compatibility` is present/reviewed (warning)

## Signing (optional)

For runtime verification, sign the manifest so the tarball includes integrity metadata:

- **Environment**: Set `SPECFACT_MODULE_PRIVATE_SIGN_KEY` (inline PEM) and `SPECFACT_MODULE_PRIVATE_SIGN_KEY_PASSPHRASE` if the key is encrypted. Or use `--key-file` and optionally `--passphrase` / `--passphrase-stdin`.
- **Re-sign after changes**: Run `scripts/sign-modules.py` on the manifest (and bump version if content changed). See [Module signing and key rotation](module-signing-and-key-rotation.md).

## GitHub Actions workflow

Repository workflow `.github/workflows/publish-modules.yml`:

- **Triggers**:
  - Push to `dev` and `main` (decoupled modules release flow)
  - Manual `workflow_dispatch` with optional `bundles` input
- **Flow**:
  - Detect changed bundles (or use manual bundle list)
  - Run `scripts/publish-module.py --bundle <name>` pre-check for each bundle
  - Package bundle into `registry/modules/<bundle>-<version>.tar.gz`
  - Update `registry/index.json` (`latest_version`, `download_url`, `checksum_sha256`, metadata)
  - Persist manifest signature copy to `registry/signatures/<bundle>-<version>.tar.sig` when present
  - Commit/push registry updates back to the same branch

## Best practices

- Bump module `version` in `module-package.yaml` whenever payload or manifest content changes; keep versions immutable for published artifacts.
- Use `namespace/name` for any module you publish to a registry.
- Run `scripts/verify-modules-signature.py --require-signature` (or your registry’s policy) before releasing.
- Prefer `--download-base-url` and `--index-fragment` when integrating with a custom registry index.

## See also

- [Module marketplace](module-marketplace.md) – Discovery, trust, and security.
- [Module signing and key rotation](module-signing-and-key-rotation.md) – Keys, signing, and verification.
- [Custom registries](custom-registries.md) – Adding and configuring registries for install/search.
