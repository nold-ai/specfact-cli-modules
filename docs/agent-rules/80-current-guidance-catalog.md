---
layout: default
title: Agent migrated guidance catalog
permalink: /contributing/agent-rules/migrated-guidance-catalog/
description: Preserved guidance moved out of the previous long AGENTS.md before further tailoring and decomposition.
keywords: [agents, migrated-guidance, code-conventions, ci, testing]
audience: [team, enterprise]
expertise_level: [advanced]
doc_owner: specfact-cli-modules
tracks:
  - AGENTS.md
  - docs/agent-rules/**
  - packages/**
  - tests/**
  - .github/workflows/**
last_reviewed: 2026-04-12
exempt: false
exempt_reason: ""
id: agent-rules-migrated-guidance-catalog
always_load: false
applies_when:
  - detailed-reference
priority: 80
blocking: false
user_interaction_required: false
stop_conditions:
  - none
depends_on:
  - agent-rules-index
---

# Agent migrated guidance catalog

This file preserves current instructions that were previously inline in the long `AGENTS.md` but are not yet fully split into narrower docs. Nothing here was intentionally dropped during the compact-governance migration.

## Code conventions

- Python 3.11+ runtime, line length 120, typed public surfaces
- `snake_case` for files, modules, and functions
- `PascalCase` for classes
- `UPPER_SNAKE_CASE` for constants
- Stable public bundle surfaces should continue to use `@beartype` and `@icontract`

## Bundle and registry reminders

- Keep bundle package code under `packages/`.
- Keep registry metadata in `registry/index.json` and `packages/*/module-package.yaml`.
- This repository hosts official nold-ai bundles only; third-party bundles publish from their own repositories.

## Testing

Contract-first coverage remains the primary testing philosophy. Test structure mirrors source under `tests/unit/`, `tests/integration/`, and `tests/e2e/`.
