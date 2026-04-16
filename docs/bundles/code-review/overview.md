---
layout: default
title: Code Review bundle overview
nav_order: 2
permalink: /bundles/code-review/overview/
keywords: [code-review, bundle, overview, review, quality]
audience: [solo, team, enterprise]
expertise_level: [beginner, intermediate]
---

# Code Review bundle overview

The **Code Review** bundle (`nold-ai/specfact-code-review`) extends the shared **`specfact code`** command group with **`review`** workflows: governed review runs, **reward ledger** history, and **house-rules** skill management.

Use it together with the [Codebase](/bundles/codebase/overview/) bundle (`import`, `analyze`, `drift`, `validate`, `repro`) on the same `code` surface.

## Prerequisites

- `specfact module install nold-ai/specfact-code-review` — the manifest `bundle_dependencies` list includes **`nold-ai/specfact-codebase`**, so SpecFact CLI **will automatically install** the Codebase bundle alongside this one for the full shared **`specfact code`** command surface (import, analyze, drift, and related commands live there).
- Optional tool installs (Ruff, Radon, Semgrep, Pyright, etc.) as described in command help

## `specfact code review` — nested commands

| Command | Purpose |
|--------|---------|
| `run` | Execute a governed review (scope, JSON output, `--fix`, TDD gate, etc.) |
| `ledger` | Inspect and update review reward history |
| `rules` | Manage the house-rules skill (`show`, `init`, `update`) |

### `ledger` subcommands

| Subcommand | Purpose |
|------------|---------|
| `update` | Update ledger entries |
| `status` | Show ledger status |
| `reset` | Reset ledger state |

### `rules` subcommands

| Subcommand | Purpose |
|------------|---------|
| `show` | Show current rules configuration |
| `init` | Initialize rules/skill assets |
| `update` | Update rules content |

## Bundle-owned skills and policy packs

House rules and review payloads ship **inside the bundle** (for example Semgrep
packs, the `specfact/clean-code-principles` policy-pack manifest, and skill
metadata). They are **not** core CLI-owned resources. Install or refresh
IDE-side assets with `specfact init ide` after upgrading the bundle.

## Quick examples

```bash
specfact code review run --help
specfact code review ledger status --help
specfact code review rules show --help
```

## See also

- [Code review run](../run/)
- [Code review ledger](../ledger/)
- [Code review rules](../rules/)
- [Code review module](/modules/code-review/)
- [Codebase bundle overview](/bundles/codebase/overview/) — import, drift, validation, repro
