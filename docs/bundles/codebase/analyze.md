---
layout: default
title: Code analyze contracts
nav_order: 3
permalink: /bundles/codebase/analyze/
redirect_from:
  - /guides/code-analyze-contracts/
---

# Code analyze contracts

`specfact code analyze contracts` measures contract coverage across the implementation files tracked by a project bundle.

## Command

- `specfact code analyze contracts`

## Key options

| Option | Purpose |
|--------|---------|
| `--repo <path>` | Point at the repository to analyze |
| `--bundle <name>` | Select the bundle explicitly instead of relying on the active plan |

## What it reports

- Files analyzed for the selected bundle
- Coverage of `beartype`, `icontract`, and CrossHair usage
- A `quality-tracking.yaml` artifact saved in the bundle directory

## Examples

```bash
specfact code analyze contracts --repo . --bundle legacy-api
specfact code analyze contracts --bundle auth-module
```

## Related

- [Code drift detect](drift/)
- [Code repro](repro/)
- [Codebase bundle overview](overview/)
