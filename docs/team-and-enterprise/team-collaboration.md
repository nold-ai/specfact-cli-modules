---
layout: default
title: Team Collaboration Setup
permalink: /team-and-enterprise/team-collaboration/
redirect_from:
  - /guides/team-collaboration-workflow/
---

# Team Collaboration Setup

This guide is for team leads who are rolling out SpecFact across a shared repository or a small set of team-owned repositories.

## 1. Bootstrap the team profile

Start from a team-oriented profile instead of a solo-developer bootstrap:

```bash
specfact init --profile backlog-team
specfact init ide --repo . --ide cursor
```

Use `backlog-team` for shared backlog and project-bundle workflows. Re-run `specfact init ide` after bundle upgrades so every developer gets the same prompt and template set from the installed modules.

## 2. Initialize project-scoped module artifacts

```bash
specfact module init --scope project --repo .
specfact project init-personas --bundle legacy-api --no-interactive
```

Use project scope when the team wants repository-local bootstrap artifacts instead of per-user defaults. `init-personas` ensures the shared bundle has the expected persona mappings before collaboration begins.

## 3. Establish shared role workflows

Typical role ownership:

- Product Owner: backlog content, readiness, prioritization
- Architect: constraints, contracts, deployment and risk
- Developer: implementation details, task mapping, definition of done

Export and import flows for each role:

```bash
specfact project export --bundle legacy-api --persona product-owner --output-dir docs/project-plans
specfact project import --bundle legacy-api --persona product-owner --input docs/project-plans/product-owner.md --dry-run
```

Repeat the same pattern for `architect` and `developer`.

## 4. Protect concurrent edits with locks

```bash
specfact project locks --bundle legacy-api
specfact project lock --bundle legacy-api --section idea --persona product-owner
```

Lock high-contention sections before edits, then unlock after import. This prevents overlapping changes when several personas work in parallel.

## 5. Merge branch-level bundle edits safely

```bash
specfact project merge \
  --bundle legacy-api \
  --base main \
  --ours feature/product-owner-updates \
  --theirs feature/architect-updates \
  --persona-ours product-owner \
  --persona-theirs architect
```

Use persona-aware merge when branches diverged on the same bundle but the changes came from different owners.

## 6. Keep bundle-owned prompts and templates aligned

Prompts and workspace templates are bundle-owned resources, not core-owned files. Team rollout should use installed module versions plus the supported bootstrap commands:

```bash
specfact module upgrade
specfact init ide --repo . --ide cursor --force
```

## Recommended team cadence

1. Bootstrap one repo with `backlog-team`.
2. Initialize personas and project-scope module artifacts.
3. Export persona views into a shared docs or planning directory.
4. Require locks for high-contention sections.
5. Refresh IDE resources whenever module versions change.

## Related

- [Agile/Scrum Team Setup](/team-and-enterprise/agile-scrum-setup/)
- [Multi-Repo Setup](/team-and-enterprise/multi-repo/)
- [Project bundle overview](/bundles/project/overview/)
