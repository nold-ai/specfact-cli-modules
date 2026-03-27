---
layout: default
title: Cross-Module Chains
permalink: /guides/cross-module-chains/
---

# Cross-Module Chains

This guide documents current multi-bundle workflows that move work from backlog planning through code, spec validation, and release enforcement.

## Prerequisite bootstrap

Run these once per repository, and again after relevant bundle upgrades:

```bash
specfact init --profile solo-developer
specfact init ide --repo . --ide cursor
```

`specfact init ide` is the supported bootstrap for bundle-owned prompts and templates used by backlog, review, and govern flows.

## Chain 1. Backlog refinement -> bundle sync

```bash
specfact backlog ceremony refinement github --preview --labels feature
specfact backlog verify-readiness --adapter github --project-id owner/repo --target-items 123
specfact project sync bridge --adapter github --mode export-only --repo . --bundle legacy-api
```

Use this chain when work starts in an external backlog tool and must be cleaned up before it becomes a SpecFact project artifact.

## Chain 2. Brownfield intake -> contract validation

```bash
specfact code import legacy-api --repo .
specfact code analyze contracts --repo . --bundle legacy-api
specfact spec validate --bundle legacy-api --force
```

Use this chain after importing a legacy repository into a project bundle and before deeper refactoring starts.

## Chain 3. Contract update -> release gate

```bash
specfact spec backward-compat api/openapi.yaml --previous api/openapi.v1.yaml
specfact spec generate-tests api/openapi.yaml
specfact govern enforce sdd legacy-api --no-interactive
```

Use this chain when a contract changed and you want compatibility checks, generated coverage, and bundle enforcement before promotion.

## Chain 4. Review loop for changed files

```bash
specfact code review run src --scope changed --no-tests
specfact govern enforce stage --preset balanced
specfact govern enforce sdd legacy-api --no-interactive
```

Use this when a branch is ready for review and you want the review bundle plus govern bundle to agree on the gate posture.

## Related

- [Daily DevOps routine](/guides/daily-devops-routine/)
- [Command chains reference](/guides/command-chains/)
- [Backlog bundle overview](/bundles/backlog/overview/)
