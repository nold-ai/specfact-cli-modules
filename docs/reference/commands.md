---
layout: default
title: Command Reference
permalink: /reference/commands/
keywords: [commands, reference, cli, syntax, usage]
audience: [solo, team, enterprise]
expertise_level: [advanced]
---

# Command Reference

SpecFact CLI ships a lean core. Workflow commands are installed from marketplace bundles.

## Top-Level Commands

Root command surface includes core commands and the mounted bundle command groups visible in `specfact --help`:

- `specfact init`
- `specfact module`
- `specfact upgrade`
- `specfact code ...`
- `specfact backlog ...`
- `specfact project ...`
- `specfact spec ...`
- `specfact govern ...`

Nested mounted groups in the current release include:

- `specfact code review ...`
- `specfact code analyze ...`
- `specfact code drift ...`
- `specfact code validate ...`
- `specfact code repro ...`
- `specfact project sync ...`
- `specfact govern enforce ...`
- `specfact govern patch ...`

Use `specfact init --profile <name>` (or `--install <list>`) to install workflow bundles.

## Bundle to Command Mapping

| Bundle ID | Main command families |
|---|---|
| `nold-ai/specfact-project` | `project`, `project sync` |
| `nold-ai/specfact-backlog` | `backlog` |
| `nold-ai/specfact-codebase` | `code import`, `code analyze`, `code drift`, `code validate`, `code repro` |
| `nold-ai/specfact-spec` | `spec` |
| `nold-ai/specfact-govern` | `govern`, `govern enforce`, `govern patch` |
| `nold-ai/specfact-code-review` | `code review` |

## Common Flows

```bash
# First run (required)
specfact init --profile solo-developer

# Install specific workflow bundle
specfact module install nold-ai/specfact-backlog

# Project workflow examples
specfact code import --repo . legacy-api
specfact sync bridge --adapter github --mode export-only --repo .

# Code workflow examples
specfact code validate sidecar init legacy-api /path/to/repo
specfact code repro --verbose

# Backlog workflow examples
specfact backlog refine --help
```

## See Also

- [Module Categories](module-categories.md)
- [Marketplace Bundles](../guides/marketplace.md)
- [Installing Modules](../guides/installing-modules.md)
