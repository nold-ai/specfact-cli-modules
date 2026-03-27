---
layout: default
title: Workflows
permalink: /workflows/
redirect_from:
  - /guides/workflows/
---

# Workflows

This index collects the current workflow guides that are aligned to the mounted command surface shipped by the installed modules in this repository.

## Start here

Run the bundle bootstrap steps before following any IDE-assisted or prompt-driven workflow:

```bash
specfact init --profile solo-developer
specfact init ide --repo . --ide cursor
```

Use `specfact init ide` again after module upgrades so bundle-owned prompts and templates stay in sync with the CLI.

## Brownfield modernization

- [Brownfield modernization](/guides/brownfield-modernization/) for the end-to-end legacy-code modernization path
- [Brownfield FAQ and ROI](/guides/brownfield-faq-and-roi/) for planning, rollout, and investment questions
- [Brownfield examples](/guides/brownfield-examples/) for concrete example flows you can adapt

## Cross-bundle delivery workflows

- [Cross-module chains](/guides/cross-module-chains/) for backlog -> code -> spec -> govern handoffs
- [Daily DevOps routine](/guides/daily-devops-routine/) for morning standup through end-of-day review
- [CI/CD pipeline](/guides/ci-cd-pipeline/) for pre-commit, GitHub Actions, and release-stage quality gates
- [Command chains reference](/guides/command-chains/) for short command sequences grouped by goal

## Focused deep dives

- [AI IDE workflow](/ai-ide-workflow/) for prompt/bootstrap-aware IDE usage
- [Contract testing workflow](/contract-testing-workflow/) for Specmatic validation, compatibility, test generation, and mocks
- [Agile/Scrum workflows](/guides/agile-scrum-workflows/) for backlog ceremonies and persona flows
- [Team collaboration workflow](/team-collaboration-workflow/) for persona export/import and lock-based editing

## Bundle references used by these workflows

- [Backlog bundle overview](/bundles/backlog/overview/)
- [Project bundle overview](/bundles/project/overview/)
- [Codebase bundle overview](/bundles/codebase/overview/)
- [Spec bundle overview](/bundles/spec/overview/)
- [Govern bundle overview](/bundles/govern/overview/)
