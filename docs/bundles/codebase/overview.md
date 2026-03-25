---
layout: default
title: Codebase bundle overview
nav_order: 2
permalink: /bundles/codebase/overview/
---

# Codebase bundle overview

The **Codebase** bundle (`nold-ai/specfact-codebase`) mounts under `specfact code` alongside the Code Review bundle. It focuses on **brownfield import**, **contract coverage analysis**, **drift detection**, **sidecar validation**, and **reproducible validation suites**.

For automated review runs (Ruff, Semgrep, ledger, rules), see [Code Review](../code-review/overview/) — also on the `code` command group.

## Prerequisites

- `specfact module install nold-ai/specfact-codebase` (often together with `nold-ai/specfact-project`)
- Python repos for import/sidecar workflows; optional tool installs (CrossHair, Specmatic, Ruff, etc.) per command help

## Command groups (`specfact code …`)

### `import` — brownfield intake

| Entry | Purpose |
|-------|---------|
| `specfact code import` (default) | Import a repository into a project bundle (`from-code` behavior; see `--help`) |
| `specfact code import from-bridge` | Import from an external bridge/export flow |

Advanced import topics: [Project import command features](../project/import-migration/) (cross-bundle).

### `analyze` — structure and contracts

| Command | Purpose |
|--------|---------|
| `contracts` | Analyze codebase for OpenAPI contract coverage and related signals |

### `drift`

| Command | Purpose |
|--------|---------|
| `detect` | Detect drift between implementation and specifications |

### `validate` — sidecar

| Command | Purpose |
|--------|---------|
| `sidecar init` | Initialize a sidecar workspace for external-repo validation |
| `sidecar run` | Run the sidecar validation pipeline |

### `repro` — reproducibility

| Command | Purpose |
|--------|---------|
| `repro` (default) | Run the full validation suite |
| `setup` | Prepare repro validation setup |

Use `specfact code repro --help` for the default invocation flags (`--repo`, `--verbose`, `--sidecar`, …).

## Bundle-owned prompts for import/generation

Import and enrichment flows may ship **prompts or helper templates** with the bundle. They are **bundle payload**, not core-owned assets. Align your IDE with `specfact init ide` after bundle upgrades.

## Quick examples

```bash
specfact code import --help
specfact code analyze contracts --help
specfact code drift detect --help
specfact code validate sidecar init my-bundle /path/to/repo
specfact code repro --verbose --repo .
```

## Deep dives

- [Sidecar validation](sidecar-validation/)
