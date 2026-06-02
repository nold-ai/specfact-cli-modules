---
layout: default
title: Project bundle overview
nav_order: 2
permalink: /bundles/project/overview/
keywords: [project, bundle, overview, management, configuration]
audience: [solo, team, enterprise]
expertise_level: [beginner, intermediate]
---

# Project bundle overview

The **Project** bundle (`nold-ai/specfact-project`) manages SpecFact **project bundles** (personas, locks, roadmap export), links them to backlog providers, coordinates **development plans** (features, stories, SDD alignment), **syncs** external tools (Spec-Kit, OpenSpec, GitHub, Linear, Jira, …), and **migrates** legacy layouts to bundle-centric structure.

## Prerequisites

- SpecFact CLI and a repository with `.specfact/` layout
- Bundle installed: `specfact module install nold-ai/specfact-project`
- For backlog-linked flows: install [Backlog](/bundles/backlog/overview/) and link a provider

## Command families

The project lifecycle surface loads from this bundle under **`specfact project`** and **`specfact project sync`**. Use each command's `--help` output after install for option-level details.

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
| `sync` | Same sync Typer as top-level `specfact project sync` (see below) |

### `specfact project version` — bundle versions

| Command | Purpose |
|--------|---------|
| `check` | Verify bundle version metadata |
| `bump` | Increment bundle version metadata |
| `set` | Set bundle version metadata explicitly |

### `specfact project sync` — bridges and automation

Use the top-level group (`specfact project sync --help`).

| Command | Purpose |
|--------|---------|
| `bridge` | Import/export bridge for external tools and adapters |
| `repository` | Repository-scoped sync operations |
| `intelligent` | Higher-level orchestrated sync |

## Related: codebase import

Brownfield **code import** (`specfact code import from-code`, `specfact code import from-bridge`) lives in the [Codebase](/bundles/codebase/overview/) bundle; it often feeds project bundles. See [Import command features](../import-migration/) for behavior that spans both bundles.

## Bundle-owned prompts and plan templates

Plan and review flows may ship **prompts or templates** with the bundle. Treat them as **bundle payload**, not core CLI sources of truth. Refresh IDE-facing resources with `specfact init ide` after upgrades so editors receive the same artifacts the CLI expects.

The project prompt set includes `/specfact.08-simplify`, which reads `.specfact/code-review-simplify.json`, groups `ai_bloat` and metadata-backed simplification findings by `intent_key`, file or domain, and rule, shows related locations, and walks the user through accept/reject/skip/explain choices before applying any simplification edit.

## Quick examples

```bash
specfact project link-backlog --adapter github --project-id owner/repo --bundle my-bundle --repo .
specfact project health-check --project-name my-bundle --repo .
specfact project sync bridge --help
specfact project version check --bundle my-bundle --repo .
```

## See also

- [DevOps flow](../devops-flow/)
- [Import command features](../import-migration/)
