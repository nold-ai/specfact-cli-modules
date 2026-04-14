---
layout: default
title: Agent repository context
permalink: /contributing/agent-rules/repository-context/
description: Project overview, key commands, architecture, and layout preserved from the previous AGENTS.md.
keywords: [agents, commands, architecture, project-overview, registry]
audience: [team, enterprise]
expertise_level: [intermediate, advanced]
doc_owner: specfact-cli-modules
tracks:
  - AGENTS.md
  - docs/agent-rules/**
  - packages/**
  - registry/index.json
  - pyproject.toml
last_reviewed: 2026-04-12
exempt: false
exempt_reason: ""
id: agent-rules-repository-context
always_load: false
applies_when:
  - repository-orientation
  - command-lookup
priority: 20
blocking: false
user_interaction_required: false
stop_conditions:
  - none
depends_on:
  - agent-rules-index
---

# Agent repository context

## Project overview

`specfact-cli-modules` hosts official nold-ai bundle packages and the module registry consumed by SpecFact CLI. The core CLI lives in the sibling `specfact-cli` repository and is installed locally through `hatch run dev-deps`.

## Essential commands

```bash
hatch env create
hatch run dev-deps
hatch run format
hatch run type-check
hatch run lint
hatch run yaml-lint
hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump
# add --require-signature for main-equivalent checks (see agent-rules/50-quality-gates-and-review.md)
hatch run contract-test
hatch run smart-test
hatch run test
hatch run specfact code review run --json --out .specfact/code-review.json
```

## Architecture

- `packages/<bundle>/` contains bundle source and `module-package.yaml`
- `registry/index.json` is the published module registry index
- `scripts/` and `tools/` hold signing, publishing, bootstrap, and validation helpers
- `src/specfact_cli_modules/` contains shared repo tooling code
- `tests/` covers bundle behavior, docs/tooling, and registry validation
- `docs/` is the Jekyll site for modules docs and reference pages
- `openspec/` holds change proposals, specs, ordering, and evidence

## Local dependency bootstrap

`hatch run dev-deps` prefers `SPECFACT_CLI_REPO` when set, otherwise a matching `../specfact-cli-worktrees/<branch>` checkout when present, then falls back to `../specfact-cli`.

## SpecFact module scopes (avoid project vs user mismatch)

Match **specfact-cli** behavior: project `.specfact/modules` wins over `~/.specfact/modules` when the same module id exists in both; the CLI may warn once per module (see `module_discovery._maybe_warn_user_shadowed_by_project` in specfact-cli).

In this checkout:

- Prefer **`specfact module init --scope project --repo .`** (and project-scoped installs) so bundled modules live under the repo, not only under user scope.
- **`SPECFACT_MODULES_REPO`** is set to the modules repo root for every **`hatch run`** (`pyproject.toml` env-vars) and via **`apply_specfact_workspace_env`** from `specfact_cli_modules.dev_bootstrap` (also used by `ensure_core_dependency`, pytest `conftest`, and `scripts/pre_commit_code_review.py`). **`SPECFACT_REPO_ROOT`** defaults to the resolved sibling/core specfact-cli checkout when discoverable.
- If you still see a precedence warning for a module id, remove the stale user copy: **`specfact module uninstall <module-id> --scope user`**, then confirm with **`specfact module list --show-origin`**.
