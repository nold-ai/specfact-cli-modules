---
layout: default
title: Agent worktrees and branching
permalink: /contributing/agent-rules/worktrees-and-branching/
description: Branch protection, worktree policy, and conflict-avoidance rules for implementation work.
keywords: [agents, worktrees, git, branching, conflicts]
audience: [team, enterprise]
expertise_level: [advanced]
doc_owner: specfact-cli-modules
tracks:
  - AGENTS.md
  - docs/agent-rules/**
  - openspec/CHANGE_ORDER.md
last_reviewed: 2026-04-12
exempt: false
exempt_reason: ""
id: agent-rules-worktrees-and-branching
always_load: false
applies_when:
  - implementation
  - branch-management
priority: 30
blocking: true
user_interaction_required: true
stop_conditions:
  - implementation requested from dev or main without override
  - conflicting worktree ownership detected
depends_on:
  - agent-rules-index
  - agent-rules-non-negotiable-checklist
---

# Agent worktrees and branching

## Branch protection

`dev` and `main` are protected. Work on `feature/*`, `bugfix/*`, `hotfix/*`, or `chore/*` branches and submit PRs to `dev`.

## Worktree policy

- The primary checkout remains the canonical `dev` workspace.
- Use worktree paths under `../specfact-cli-modules-worktrees/<branch-type>/<branch-slug>`.
- Derive the absolute worktree root from the repository parent directory. For this repo, `../specfact-cli-modules-worktrees/` resolves under `/home/dom/git/nold-ai/`, so do not collapse the path to `/home/dom/git/specfact-cli-modules-worktrees/...` when rendering or repairing worktree locations.
- Never create a worktree for `dev` or `main`.
- One branch maps to one worktree path at a time.
- Keep one active OpenSpec change scope per branch where possible.
- Create a dedicated virtual environment inside each worktree.
- Bootstrap Hatch once per new worktree with `hatch env create` and `hatch run dev-deps`.
- Run quick pre-flight checks from the worktree root with `hatch run smart-test-status` and `hatch run contract-test-status` when those environments are available.

## Conflict avoidance

- Check `openspec/CHANGE_ORDER.md` before creating a new worktree.
- Avoid concurrent branches editing the same `openspec/changes/<change-id>/` directory.
- Rebase or fast-forward frequently on `origin/dev`.
- Use `git worktree list` to detect stale or incorrect attachments.
