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
hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump
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
