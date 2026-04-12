---
layout: default
title: Agent rules index
permalink: /contributing/agent-rules/
description: Canonical deterministic loader for repository governance instructions used by AGENTS.md and other AI instruction surfaces.
keywords: [agents, governance, instructions, openspec, worktree]
audience: [team, enterprise]
expertise_level: [advanced]
doc_owner: specfact-cli-modules
tracks:
  - AGENTS.md
  - CLAUDE.md
  - .cursorrules
  - .github/copilot-instructions.md
  - docs/agent-rules/**
  - scripts/validate_agent_rule_applies_when.py
last_reviewed: 2026-04-12
exempt: false
exempt_reason: ""
id: agent-rules-index
always_load: true
applies_when:
  - session-bootstrap
priority: 0
blocking: true
user_interaction_required: false
stop_conditions:
  - canonical rule index missing
depends_on: []
---

# Agent rules index

This page is the canonical loader for repository governance instructions. `AGENTS.md` stays small and mandatory, but the detailed rules live here and in the linked rule files so new sessions do not have to absorb the full policy corpus up front.

## Bootstrap sequence

1. Read `AGENTS.md`.
2. Load this index.
3. Load [`05-non-negotiable-checklist.md`](./05-non-negotiable-checklist.md).
4. Load [`10-session-bootstrap.md`](./10-session-bootstrap.md).
5. Detect repository, branch, and worktree state.
6. Reject implementation from the `dev` or `main` checkout unless the user explicitly overrides that rule.
7. If GitHub hierarchy metadata is needed and `.specfact/backlog/github_hierarchy_cache.md` is missing or stale, refresh it with `python scripts/sync_github_hierarchy_cache.py`.
8. Load additional rule files from the applicability matrix below before implementation.

## Precedence

1. Direct system and developer instructions
2. Explicit user override where repository governance allows it
3. `AGENTS.md`
4. `docs/agent-rules/05-non-negotiable-checklist.md`
5. Other `docs/agent-rules/*.md` files selected through this index
6. Change-local OpenSpec artifacts and workflow notes

## Always-load rules

| Order | File | Purpose |
| --- | --- | --- |
| 0 | `INDEX.md` | Deterministic rule dispatch and precedence |
| 5 | `05-non-negotiable-checklist.md` | Invariant SHALL gates |
| 10 | `10-session-bootstrap.md` | Startup checks and stop conditions |

## Applicability matrix

### Task signal definitions

Use these canonical `applies_when` tokens in rule file frontmatter under `docs/agent-rules/*.md`.

| Canonical signal | Typical user intent |
| --- | --- |
| `session-bootstrap` | First-load and startup sequencing |
| `implementation` | Code or behavior change in a worktree |
| `openspec-change-selection` | Choosing, validating, or editing an OpenSpec change |
| `branch-management` | Branch and worktree operations |
| `github-public-work` | Public-repo GitHub issue linkage and hierarchy |
| `change-readiness` | Pre-flight metadata completeness before implementation |
| `finalization` | Closing out a change, evidence, or PR |
| `release` | Versioning, tagging, publish prep |
| `documentation-update` | User-facing docs and README edits |
| `repository-orientation` | Onboarding and repo layout questions |
| `command-lookup` | Hatch commands and workflow lookup |
| `detailed-reference` | Long-form catalog and preserved guidance |
| `verification` | Quality gates, tests, and review artifacts |

**Validation:** `hatch run validate-agent-rule-signals` runs `scripts/validate_agent_rule_applies_when.py` and checks every rule file's `applies_when` list against this set.

| Matrix row (human summary) | Canonical signals (`applies_when`) | Required rule files | Optional rule files |
| --- | --- | --- | --- |
| Any implementation request | `implementation`, `openspec-change-selection`, `verification` | `10-session-bootstrap.md`, `40-openspec-and-tdd.md`, `50-quality-gates-and-review.md` | `20-repository-context.md` |
| Code or docs changes on a branch | `branch-management`, `implementation` | `30-worktrees-and-branching.md` | `80-current-guidance-catalog.md` |
| Public GitHub issue work | `github-public-work`, `change-readiness` | `60-github-change-governance.md` | `30-worktrees-and-branching.md` |
| Release or finalization work | `finalization`, `release`, `documentation-update`, `verification` | `70-release-commit-and-docs.md`, `50-quality-gates-and-review.md` | `80-current-guidance-catalog.md` |
| Repo orientation or command lookup | `repository-orientation`, `command-lookup` | `20-repository-context.md` | `80-current-guidance-catalog.md` |

## Canonical rule files

- [`05-non-negotiable-checklist.md`](./05-non-negotiable-checklist.md): always-load SHALL gates
- [`10-session-bootstrap.md`](./10-session-bootstrap.md): startup checks, compact context loading, and stop behavior
- [`20-repository-context.md`](./20-repository-context.md): project overview, commands, architecture, and layout
- [`30-worktrees-and-branching.md`](./30-worktrees-and-branching.md): branch protection, worktree policy, and conflict avoidance
- [`40-openspec-and-tdd.md`](./40-openspec-and-tdd.md): OpenSpec selection, change validity, strict TDD order, and archive rules
- [`50-quality-gates-and-review.md`](./50-quality-gates-and-review.md): required gates, code review JSON, clean-code enforcement, module signatures
- [`60-github-change-governance.md`](./60-github-change-governance.md): cache-first GitHub metadata, dependency completeness, and `in progress` ambiguity handling
- [`70-release-commit-and-docs.md`](./70-release-commit-and-docs.md): versioning, registry/signature consistency, docs, and release prep
- [`80-current-guidance-catalog.md`](./80-current-guidance-catalog.md): preserved migrated guidance not yet split into narrower documents

## Preservation note

The prior long `AGENTS.md` content has been preserved by reference in these rule files. The goal of this migration is to reduce startup token cost without silently dropping repository instructions.
