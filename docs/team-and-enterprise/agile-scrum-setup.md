---
layout: default
title: Agile And Scrum Team Setup
permalink: /team-and-enterprise/agile-scrum-setup/
redirect_from:
  - /guides/agile-scrum-workflows/
---

# Agile And Scrum Team Setup

This playbook translates the backlog and project-bundle commands into team onboarding steps for Scrum and Kanban groups.

## 1. Choose the team bootstrap profile

```bash
specfact init --profile backlog-team
specfact init ide --repo . --ide cursor
```

For API-heavy teams that also own contract workflows, move to `api-first-team` instead.

## 2. Configure the team’s backlog operating model

Primary ceremony commands:

```bash
specfact backlog ceremony standup github
specfact backlog ceremony refinement github --preview --labels feature
specfact backlog verify-readiness --adapter github --project-id owner/repo --target-items 123
```

Use standup for daily visibility, refinement for standardization, and verify-readiness before sprint commitment or release planning.

## 3. Scrum setup

Use Scrum when the team commits to iterations and wants readiness checks before sprint planning:

- Run standup against the active sprint or iteration
- Refine backlog items before they enter sprint planning
- Validate readiness before commitment
- Export persona-owned plan views when product, architecture, and development need separate edit streams

## 4. Kanban setup

Use Kanban when the team works from a continuous queue:

- Run standup without sprint filters
- Use refinement continuously on incoming work
- Use readiness checks on pull-ready or release-candidate items
- Keep unassigned work visible for pull-based planning

## 5. Shared team rollout for prompts and templates

Backlog refinement and standup support bundle-owned prompts and templates. Keep them aligned through installed module versions and re-bootstrap the IDE exports after upgrades:

```bash
specfact module upgrade
specfact init ide --repo . --ide cursor --force
```

## Related

- [Team Collaboration Setup](/team-and-enterprise/team-collaboration/)
- [Backlog bundle overview](/bundles/backlog/overview/)
- [Workflows](/workflows/)
