---
layout: default
title: Govern bundle overview
nav_order: 2
permalink: /bundles/govern/overview/
---

# Govern bundle overview

The **Govern** bundle (`nold-ai/specfact-govern`) adds **enforcement** and **patch-mode** workflows: configure quality gates tied to SDD plans, and preview/apply patches with explicit write controls.

## Prerequisites

- `specfact module install nold-ai/specfact-govern`
- Project bundles with SDD manifests when using SDD enforcement paths

## `specfact govern enforce`

| Command | Purpose |
|--------|---------|
| `stage` | Configure enforcement stages for bundles and plans |
| `sdd` | Enforce SDD quality gates against manifests and plans |

## `specfact govern patch`

| Command | Purpose |
|--------|---------|
| `apply` | Preview and apply patches (local or upstream with `--write`) |

## Bundle-owned policy packs

Enforcement may ship **bundle-local policy packs or presets** with the package. Treat them as **bundle payload** referenced by the govern module, not as core CLI-owned configuration. Refresh IDE-facing resources with `specfact init ide` when your team updates bundles.

## Quick examples

```bash
specfact govern --help
specfact govern enforce stage --help
specfact govern enforce sdd --help
specfact govern patch apply --help
```

## See also

- [Command reference](../../reference/commands/) — nested `govern` commands
