---
layout: default
title: Command Reference
permalink: /reference/commands/
---

# Command Reference

SpecFact CLI ships a lean core. Workflow commands are installed from marketplace bundles.

## Top-Level Commands

Root command surface includes core commands and installed command groups:

- `specfact init`
- `specfact auth`
- `specfact module`
- `specfact upgrade`
- `specfact plan ...`
- `specfact sync ...`
- `specfact code ...`
- `specfact backlog ...`
- `specfact project ...`
- `specfact spec ...`
- `specfact enforce ...`
- `specfact analyze ...`
- `specfact drift ...`
- `specfact validate ...`
- `specfact repro ...`
- `specfact generate ...`
- `specfact sdd ...`
- `specfact contract ...`
- `specfact review`

Use `specfact init --profile <name>` (or `--install <list>`) to install workflow bundles.

## Bundle to Command Mapping

| Bundle ID | Main command families |
|---|---|
| `nold-ai/specfact-project` | `plan`, `project`, `sync`, `migrate`, `code import` |
| `nold-ai/specfact-backlog` | `backlog` |
| `nold-ai/specfact-codebase` | `code import`, `analyze`, `drift`, `validate`, `repro` |
| `nold-ai/specfact-spec` | `spec`, `contract`, `sdd`, `generate` |
| `nold-ai/specfact-govern` | `enforce` |
| `nold-ai/specfact-code-review` | `review` |

## Common Flows

```bash
# First run (required)
specfact init --profile solo-developer

# Install specific workflow bundle
specfact module install nold-ai/specfact-backlog

# Project workflow examples
specfact code import legacy-api --repo .
specfact plan init my-project

# Code workflow examples
specfact validate sidecar init legacy-api /path/to/repo
specfact repro --verbose

# Backlog workflow examples
specfact backlog refine --help
```

## See Also

- [Module Categories](module-categories.md)
- [Marketplace Bundles](../guides/marketplace.md)
- [Installing Modules](../guides/installing-modules.md)
