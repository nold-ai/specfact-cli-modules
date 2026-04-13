---
layout: default
title: Agent OpenSpec and TDD
permalink: /contributing/agent-rules/openspec-and-tdd/
description: OpenSpec selection, change validation, and strict TDD order for behavior changes.
keywords: [agents, openspec, tdd, change-validation, evidence]
audience: [team, enterprise]
expertise_level: [advanced]
doc_owner: specfact-cli-modules
tracks:
  - AGENTS.md
  - openspec/config.yaml
  - openspec/CHANGE_ORDER.md
  - docs/agent-rules/**
last_reviewed: 2026-04-12
exempt: false
exempt_reason: ""
id: agent-rules-openspec-and-tdd
always_load: false
applies_when:
  - implementation
  - openspec-change-selection
priority: 40
blocking: true
user_interaction_required: true
stop_conditions:
  - no valid OpenSpec change
  - change stale or superseded
  - failing-before evidence missing
depends_on:
  - agent-rules-index
  - agent-rules-non-negotiable-checklist
---

# Agent OpenSpec and TDD

## OpenSpec workflow

- Before modifying application code, verify that an active OpenSpec change explicitly covers the requested modification.
- Skip only when the user explicitly says `skip openspec` or `implement without openspec change`.
- The existence of any open change is not sufficient; the change must cover the requested scope.
- If no change exists, clarify whether the work needs a new change, a modified existing change, or a delta.

## Paired public context

This modules repository does not require a sibling internal wiki checkout. When a modules change is explicitly paired with work in `specfact-cli`, use the paired public change, issue, and spec artifacts there as read-only context before changing shared workflow semantics.

## Change validity

- Never implement from a change id alone.
- Revalidate the selected change against current repository reality, dependency state, and possible superseding work.
- Use `openspec validate <change-id> --strict` to capture dependency and interface impact before implementation and before finalization.

## Strict TDD order

1. Update or add spec deltas first.
2. Add or modify tests mapped to spec scenarios.
3. Run tests and capture a failing result before production edits.
4. Only then modify production code.
5. Re-run tests and quality gates until passing.

## Evidence

Record the failing-before and passing-after runs in `openspec/changes/<change-id>/TDD_EVIDENCE.md`. Behavior work is blocked until failing-first evidence exists.

## Archive after merge

- When a change is implemented and merged, finalize it only with the OpenSpec CLI: `openspec archive <change-id>`.
- The CLI merges delta specs into `openspec/specs/` and moves the change into `openspec/changes/archive/`.
- Do not manually move or rename `openspec/changes/<change-id>/`.
