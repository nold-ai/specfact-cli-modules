---
layout: default
title: Backlog bundle overview
nav_order: 2
permalink: /bundles/backlog/overview/
keywords: [backlog, bundle, overview, refinement, stories]
audience: [solo, team, enterprise]
expertise_level: [beginner, intermediate]
---

# Backlog bundle overview

The **Backlog** bundle (`nold-ai/specfact-backlog`) connects SpecFact to external backlog tools (GitHub Issues, Azure DevOps, and other adapters), adds ceremony-oriented workflows, dependency analysis, delta tracking, and deterministic backlog policy checks.

## Prerequisites

- [SpecFact CLI](https://docs.specfact.io) installed
- Bundle installed: `specfact module install nold-ai/specfact-backlog` (or include it via `specfact init --profile …`)
- For provider access: configure tokens or use `specfact backlog auth` where your adapter requires it

## Command surface

After installation, `specfact backlog --help` lists the backlog command group. The backlog category also mounts **policy** as `specfact backlog policy` (see below).

### Ceremony (`specfact backlog ceremony`)

| Command | Purpose |
|--------|---------|
| `standup` | Alias for daily standup-style views (`backlog daily`) |
| `refinement` | Alias for AI-assisted refinement (`backlog refine`) |
| `planning` | Delegates to sprint-summary style flows when available |
| `flow` | Kanban-style flow views when available |
| `pi-summary` | PI summary views when available |

### Core workflows

| Command | Purpose |
|--------|---------|
| `daily` | Daily standup table: filtered items, optional interactive mode, summarize prompts |
| `refine` | AI-assisted template-driven refinement (preview/write, filters, DoR checks) |
| `add` | Create backlog items with hierarchy and Definition-of-Ready validation |
| `sync` | Sync backlog graph with stored baseline and export delta outputs |
| `verify-readiness` | Verify release readiness for selected backlog items |
| `analyze-deps` | Analyze backlog dependencies for a project |
| `diff` | Show changes since baseline sync |
| `promote` | Validate promotion impact and print promotion intent |
| `init-config` | Scaffold `.specfact/backlog-config.yaml` structure |
| `map-fields` | Interactive mapping of ADO fields to canonical names |

### Delta (`specfact backlog delta`)

| Command | Purpose |
|--------|---------|
| `status` | Compare current graph to baseline; show delta summary |
| `impact` | Downstream dependency impact for an item |
| `cost-estimate` | Rough effort points from delta volume |
| `rollback-analysis` | Rollback risk from current delta |

## Local artifact ownership

Backlog runtime state is expected to live under `.specfact/`.

- `.specfact/backlog-config.yaml` is a partially user-tuned config file. Backlog commands update only the managed provider subtree and preserve unrelated settings.
- `.specfact/templates/backlog/field_mappings/ado_custom.yaml` is also partially user-tuned. `specfact backlog map-fields` preserves unrelated top-level sections and fails safe if the existing file is not a valid YAML mapping.
- `.specfact/backlog-baseline.json` and generated files under `.specfact/plans/` are SpecFact-managed state and may be rewritten deterministically.
- If you point `specfact backlog sync --baseline-file` to an existing path outside `.specfact`, SpecFact treats that file as user-owned and requires `--force-baseline-overwrite` before replacement. The previous file is backed up under `.specfact/recovery/`.

### Policy (`specfact backlog policy`)

Deterministic policy validation against backlog snapshots (bundled with this package; not core CLI-owned).

| Command | Purpose |
|--------|---------|
| `init` | Scaffold `.specfact/policy.yaml` from a template |
| `validate` | Run policy checks (JSON/Markdown/both) |
| `suggest` | Patch-ready suggestions (no automatic writes) |

See [Policy engine](../policy-engine/) for details.

### Auth (`specfact backlog auth`)

Backlog provider authentication for **GitHub** and **Azure DevOps**: store tokens, run OAuth / device-code flows, inspect status, and clear credentials for setup and troubleshooting.

| Subcommand | Purpose |
|------------|---------|
| `azure-devops` | Authenticate to Azure DevOps via PAT (`--pat`) or OAuth (interactive browser or `--use-device-code`) |
| `github` | Authenticate to GitHub (or GitHub Enterprise) via RFC 8628 device code flow; optional `--client-id`, `--base-url`, `--scopes` |
| `status` | Show stored auth state for supported providers (valid vs expired tokens) |
| `clear` | Remove stored tokens; optional `--provider` (`azure-devops` or `github`) or omit to clear all |

## Bundle-owned prompts and templates

Refinement and ceremony flows **emit prompts and instructions** for your IDE copilot. Those assets ship with the backlog bundle (and related payloads); they are **not** maintained as core CLI-owned files. Install or refresh IDE resources with `specfact init ide` (and your team’s bundle publishing workflow) so the CLI and bundles stay aligned.

## Quick examples

Validate the exact flags for your adapter:

```bash
specfact backlog daily --help
specfact backlog refine --help
specfact backlog delta status --help
specfact backlog policy validate --help
specfact backlog auth --help
specfact backlog auth status --help
specfact backlog auth github --help
```

GitHub refinement preview (typical entry point):

```bash
specfact backlog refine github --preview --labels feature
```

Daily standup scope:

```bash
specfact backlog daily github --state open --limit 20
```

## Deep dives

- [Refinement](../refinement/)
- [Dependency analysis](../dependency-analysis/)
- [Delta](../delta/)
- [Policy engine](../policy-engine/)
