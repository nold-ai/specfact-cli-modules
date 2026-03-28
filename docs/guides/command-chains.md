---
layout: default
title: Command Chains Reference
permalink: /guides/command-chains/
keywords: [command-chains, workflow, automation, sequences, cli]
audience: [solo, team]
expertise_level: [intermediate]
---

# Command Chains Reference

Use this page when you need a short, validated command chain for a common task. Each chain uses current mounted commands and links to the deeper workflow guide that explains the decision points.

## 1. Bootstrap a workflow-ready repository

```bash
specfact init --profile solo-developer
specfact init ide --repo . --ide cursor
specfact module install nold-ai/specfact-backlog
```

Use this before any workflow that depends on bundle-owned prompts or templates.

Related: [AI IDE workflow](/ai-ide-workflow/)

## 2. Brownfield intake and contract discovery

```bash
specfact code import legacy-api --repo .
specfact code analyze contracts --repo . --bundle legacy-api
specfact spec validate --bundle legacy-api --force
```

Use this when you need a project bundle, contract-coverage visibility, and a first validation pass for a legacy codebase.

Related: [Brownfield modernization](/guides/brownfield-modernization/)

## 3. Refine backlog work before sync/export

```bash
specfact backlog ceremony refinement github --preview --labels feature
specfact backlog verify-readiness --adapter github --project-id owner/repo --target-items 123
specfact sync bridge --adapter github --mode export-only --repo . --bundle legacy-api
```

Use this chain when backlog items must be standardized and readiness-checked before you export or sync them into project artifacts.

Related: [Cross-module chains](/guides/cross-module-chains/)

## 4. Specmatic validation and compatibility

```bash
specfact spec validate api/openapi.yaml
specfact spec backward-compat api/openapi.yaml --previous api/openapi.v1.yaml
specfact spec generate-tests api/openapi.yaml
```

Use this chain when you are validating a contract update and need generated test coverage before release review.

Related: [Contract testing workflow](/contract-testing-workflow/)

## 5. Daily review and cleanup

```bash
specfact backlog ceremony standup github
specfact code review run docs/guides/cross-module-chains.md --no-tests
specfact govern enforce sdd legacy-api --no-interactive
```

Use this chain to review backlog state, run a scoped quality review, and validate release readiness on a bundle before you stop for the day.

Related: [Daily DevOps routine](/guides/daily-devops-routine/)

## 6. CI-ready local gate run

```bash
hatch run format
hatch run type-check
hatch run lint
hatch run yaml-lint
hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump
hatch run contract-test
hatch run smart-test
hatch run test
```

Use this chain as the full required pre-push gate order so the local run matches the repository CI quality gates.

Related: [CI/CD pipeline](/guides/ci-cd-pipeline/)
