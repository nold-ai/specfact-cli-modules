---
layout: default
title: Project bundle overview
nav_order: 2
permalink: /bundles/project/overview/
---

# Project bundle overview

The **Project** bundle (`nold-ai/specfact-project`) manages SpecFact **project bundles** (personas, locks, roadmap export), links them to backlog providers, coordinates **development plans** (features, stories, SDD alignment), **syncs** external tools (Spec-Kit, OpenSpec, GitHub, Linear, Jira, …), and **migrates** legacy layouts to bundle-centric structure.

## Prerequisites

- SpecFact CLI and a repository with `.specfact/` layout
- Bundle installed: `specfact module install nold-ai/specfact-project`
- For backlog-linked flows: install [Backlog](../backlog/overview/) and link a provider

## Command families

The project lifecycle surface loads from this bundle across **`specfact project`**, **`specfact plan`**, top-level **`specfact sync`**, and **`specfact migrate`** (see each group’s `--help` after install). The `project` group also nests a `sync` Typer; prefer the **top-level** `specfact sync …` entry when documented in the command reference.

### `specfact project` — bundles and personas

| Command | Purpose |
|--------|---------|
| `link-backlog` | Link a project bundle to a backlog adapter and project id |
| `health-check` | Project health including backlog graph checks |
| `devops-flow` | Integrated DevOps stage actions for a linked bundle |
| `snapshot` | Save the linked backlog graph as a baseline snapshot |
| `regenerate` | Re-derive plan state from bundle + backlog graph |
| `export-roadmap` | Export roadmap milestones from dependency critical path |
| `export` | Export persona-owned sections to Markdown |
| `import` | Import persona-edited Markdown back into the bundle |
| `lock` / `unlock` / `locks` | Section locks for collaborative editing |
| `init-personas` | Initialize persona mappings in the manifest |
| `merge` | Three-way merge with persona-aware conflict handling |
| `resolve-conflict` | Resolve a specific merge conflict |
| `version` | Subcommands for bundle versioning |
| `sync` | Same sync Typer as top-level `specfact sync` (see below) |

### `specfact plan` — plans, stories, and reviews

| Command | Purpose |
|--------|---------|
| `init` | Initialize or adopt a development plan for a bundle |
| `add-feature` / `add-story` | Add plan items |
| `update-idea` / `update-feature` / `update-story` | Update plan content |
| `compare` | Compare manual vs automatic plan inputs |
| `select` | Select active plan context |
| `upgrade` | Upgrade plan artifacts |
| `sync` | Sync plan artifacts with repo state |
| `promote` | Promotion workflow for plan readiness |
| `review` | Plan review workflows |
| `harden` | Harden SDD and related artifacts |

### `specfact sync` — bridges and automation

Use the top-level group (`specfact sync --help`).

| Command | Purpose |
|--------|---------|
| `bridge` | Import/export bridge for external tools and adapters |
| `repository` | Repository-scoped sync operations |
| `intelligent` | Higher-level orchestrated sync |

### `specfact migrate` — structure migrations

| Command | Purpose |
|--------|---------|
| `cleanup-legacy` | Remove empty legacy top-level directories under `.specfact/` |
| `to-contracts` | Migrate verbose bundles toward contract-oriented layouts |
| `artifacts` | Migrate plan and artifact layouts |

## Related: codebase import

Brownfield **code import** (`specfact code import`, `specfact import …`) lives in the [Codebase](../codebase/overview/) bundle; it often feeds project bundles. See [Import command features](import-migration/) for behavior that spans both bundles.

## Bundle-owned prompts and plan templates

Plan and review flows may ship **prompts or templates** with the bundle. Treat them as **bundle payload**, not core CLI sources of truth. Refresh IDE-facing resources with `specfact init ide` after upgrades so editors receive the same artifacts the CLI expects.

## Quick examples

```bash
specfact project link-backlog --adapter github --project-id owner/repo --bundle my-bundle --repo .
specfact plan init --help
specfact sync bridge --help
specfact migrate artifacts --repo .
```

## See also

- [DevOps flow](devops-flow/)
- [Import command features](import-migration/)
