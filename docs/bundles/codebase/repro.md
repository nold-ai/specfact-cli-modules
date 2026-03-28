---
layout: default
title: Code repro
nav_order: 5
permalink: /bundles/codebase/repro/
redirect_from:
  - /guides/code-repro/
keywords: [repro, codebase, reproduction, debugging, validation]
audience: [solo, team, enterprise]
expertise_level: [intermediate, advanced]
---

# Code repro

`specfact code repro` runs the reproducibility suite, and `specfact code repro setup` prepares CrossHair configuration for deeper contract exploration.

## Commands

- `specfact code repro`
- `specfact code repro setup`

## `specfact code repro`

Use the main repro command to run lint, type, contract, and optional sidecar checks against a repository.

| Option | Purpose |
|--------|---------|
| `--repo <path>` | Choose the repository to validate |
| `--out <path>` | Write a report file |
| `--verbose` | Print more detailed execution output |
| `--fail-fast` | Stop at the first failure |
| `--fix` | Apply available autofixes before rerunning |
| `--crosshair-required` | Fail when CrossHair is skipped or fails |
| `--crosshair-per-path-timeout <seconds>` | Increase deep CrossHair exploration time |
| `--sidecar` | Run sidecar validation for unannotated code |
| `--sidecar-bundle <name>` | Choose the bundle used for sidecar validation |

Examples:

```bash
specfact code repro --repo .
specfact code repro --repo /path/to/external/repo --verbose
specfact code repro --fix --repo .
specfact code repro --sidecar --sidecar-bundle legacy-api --repo /path/to/repo
```

## `specfact code repro setup`

Use the setup command to add a `[tool.crosshair]` section to `pyproject.toml` and prepare the repo for contract exploration.

| Option | Purpose |
|--------|---------|
| `--repo <path>` | Choose the repository to configure |
| `--install-crosshair` | Attempt to install `crosshair-tool` if it is missing |

Examples:

```bash
specfact code repro setup
specfact code repro setup --repo /path/to/repo
specfact code repro setup --install-crosshair
```

## Related

- [Code analyze contracts](analyze/)
- [Code drift detect](drift/)
- [Sidecar validation](sidecar-validation/)
