---
layout: default
title: Govern bundle overview
nav_order: 2
permalink: /bundles/govern/overview/
keywords: [govern, bundle, overview, policy, compliance]
audience: [solo, team, enterprise]
expertise_level: [beginner, intermediate]
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

Enforcement may ship **bundle-local policy packs or presets** with the package. Treat them as **bundle payload** referenced by the govern module, not as core CLI-owned configuration. Refresh IDE-facing resources with `specfact init ide` (core IDE prompts from installed modules). The **Code Review** bundle (`nold-ai/specfact-code-review`) provides `specfact code review rules init --ide` and `specfact code review rules update --ide` (e.g. `--ide cursor`, `--ide claude`, `--ide codex`, or `--ide vibe`; see `--help`) for the house-rules skill—install that bundle separately when you need those commands.

## Quick examples

```bash
specfact govern --help
specfact govern enforce stage --help
specfact govern enforce sdd --help
specfact govern patch apply --help
```

## See also

- [Govern enforce](../enforce/)
- [Govern patch](../patch/)
- [Command reference](/reference/commands/) — nested `govern` commands
