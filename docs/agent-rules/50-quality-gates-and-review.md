---
layout: default
title: Agent quality gates and review
permalink: /contributing/agent-rules/quality-gates-and-review/
description: Required formatting, typing, signing, testing, and review gates for touched scope.
keywords: [agents, quality, review, contracts, signatures]
audience: [team, enterprise]
expertise_level: [advanced]
doc_owner: specfact-cli-modules
tracks:
  - AGENTS.md
  - pyproject.toml
  - scripts/pre_commit_code_review.py
  - scripts/verify-modules-signature.py
  - docs/agent-rules/**
last_reviewed: 2026-04-12
exempt: false
exempt_reason: ""
id: agent-rules-quality-gates-and-review
always_load: false
applies_when:
  - implementation
  - verification
  - finalization
priority: 50
blocking: true
user_interaction_required: false
stop_conditions:
  - required quality gate failed
  - specfact code review findings unresolved
  - module signature verification failed
depends_on:
  - agent-rules-index
  - agent-rules-openspec-and-tdd
---

# Agent quality gates and review

## Quality gate order

1. `hatch run format`
2. `hatch run type-check`
3. `hatch run lint`
4. `hatch run yaml-lint`
5. `hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`
6. `hatch run contract-test`
7. `hatch run smart-test`
8. `hatch run test`

## Pre-commit order

1. Module signature verification (`.pre-commit-config.yaml`, `fail_fast: true` so a failing earlier hook never runs later stages).
2. `scripts/pre-commit-quality-checks.sh` — **Block 1:** `hatch run format` (fails if reformatting would change the tree), conditional YAML / bundle-import / lint checks. **Block 2** (skipped for “safe-only” staged paths): `hatch run python scripts/pre_commit_code_review.py …` on staged Python sources, then `contract-test-status` / `hatch run contract-test` with visible stage labels in the script output.

## SpecFact code review JSON

- Treat `.specfact/code-review.json` as mandatory evidence before an OpenSpec change is complete.
- Re-run the review when the report is missing or stale.
- Resolve every finding at any severity unless a rare, explicit exception is documented.
- Record the review command and timestamps in `TDD_EVIDENCE.md` or the PR description when quality gates are part of the change.

## Clean-code review gate

The repository enforces the clean-code charter through `specfact code review run`. Zero regressions in `naming`, `kiss`, `yagni`, `dry`, and `solid` are required before merge.

## Module signature gate

Any change that affects signed module assets or manifests must pass the signature verification command above. If verification fails because bundle contents changed, re-sign the affected manifests and bump the module version before re-running verification.
