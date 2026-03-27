---
layout: default
title: Daily DevOps Routine
permalink: /guides/daily-devops-routine/
---

# Daily DevOps Routine

This guide shows a full work day that spans backlog, code review, contract validation, and enforcement.

## 1. Morning standup and queue check

```bash
specfact backlog ceremony standup github
```

Use this to see active work, blockers, and the items you should commit to next.

Reference: [Backlog bundle overview](/bundles/backlog/overview/)

## 2. Refine or verify work before development

```bash
specfact backlog ceremony refinement github --preview --labels feature
specfact backlog verify-readiness --adapter github --project-id owner/repo --target-items 123
```

Use refinement when the work item needs structure. Use readiness verification when you need a release- or planning-grade check.

Reference: [Cross-module chains](/guides/cross-module-chains/)

## 3. Development and bundle refresh

```bash
specfact init ide --repo . --ide cursor
specfact code import legacy-api --repo .
```

Refresh IDE resources when the workflow depends on installed prompts, then import or refresh the project bundle before deeper validation.

Reference: [AI IDE workflow](/guides/ai-ide-workflow/)

## 4. Midday quality review

```bash
specfact code review run src --scope changed --no-tests
specfact spec validate --bundle legacy-api
```

Run the review bundle on your changed files and validate the affected contracts while the context is still fresh.

Reference: [Contract testing workflow](/guides/contract-testing-workflow/)

## 5. End-of-day release readiness

```bash
specfact govern enforce sdd legacy-api --no-interactive
```

Use this before pushing or opening a promotion-oriented PR so the bundle state, manifest, and contracts are checked together.

Reference: [Govern enforce](/bundles/govern/enforce/)
