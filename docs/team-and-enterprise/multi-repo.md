---
layout: default
title: Multi-Repo Setup
permalink: /team-and-enterprise/multi-repo/
keywords: [multi-repo, monorepo, setup, enterprise, organization]
audience: [team, enterprise]
expertise_level: [intermediate]
---

# Multi-Repo Setup

Use this guide when one team manages several repositories that share the same module stack or bundle rollout policy.

## 1. Standardize the bootstrap across repos

Use the same profile in each repository:

```bash
specfact init --profile enterprise-full-stack
specfact init ide --repo . --ide cursor
specfact module init --scope project --repo .
```

This gives each repo the same baseline while still allowing repository-local artifacts.

## 2. Use `--repo` explicitly for repository-specific actions

Commands that support `--repo` should point to the active repository when automation runs across several working copies:

```bash
specfact project export --repo /workspace/service-a --bundle service-a --persona architect --stdout
specfact project import --repo /workspace/service-b --bundle service-b --persona developer --input docs/project-plans/developer.md --dry-run
specfact sync bridge --adapter github --mode export-only --repo /workspace/service-a --bundle service-a
```

## 3. Keep shared module rollout predictable

Prompts and templates come from installed bundles, so multi-repo teams should align on:

- the profile used for first bootstrap
- the module versions promoted across repositories
- when `specfact init ide --force` is re-run after upgrades

## 4. Use repo-local overrides where needed

Project-scope module bootstrap is the safe place for repo-specific behavior:

```bash
specfact module init --scope project --repo /workspace/service-a
```

Use that when one repository needs additional local artifacts without changing the user-scoped defaults for every repo on a developer workstation.

## Related

- [Enterprise Configuration](/team-and-enterprise/enterprise-config/)
- [Team Collaboration Setup](/team-and-enterprise/team-collaboration/)
- [Project bundle overview](/bundles/project/overview/)
