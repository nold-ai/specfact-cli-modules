---
layout: default
title: AI IDE Workflow Guide
permalink: /ai-ide-workflow/
redirect_from:
  - /guides/ai-ide-workflow/
---

# AI IDE Workflow Guide

This guide covers the current IDE-assisted workflow for bundle-owned prompts and templates. The key rule is simple: bootstrap resources through the CLI, not by copying files from legacy core-owned paths.

## 1. Bootstrap the repository and IDE resources

```bash
specfact init --profile solo-developer
specfact init ide --repo . --ide cursor
```

`specfact init ide` exports prompts from core plus installed modules. Re-run it after bundle upgrades or when you install an additional workflow bundle.

## 2. Confirm the modules that own the prompts you need

```bash
specfact module install nold-ai/specfact-backlog
specfact module install nold-ai/specfact-govern
specfact module install nold-ai/specfact-code-review
```

Typical ownership:

- Backlog refinement and ceremony prompts come from the Backlog bundle
- Govern presets and policy-oriented prompt flows come from the Govern bundle
- Review house-rules flows come from the Code Review bundle

## 3. Run the CLI step that emits or consumes the prompt

Examples:

```bash
specfact backlog ceremony refinement github --preview --labels feature
specfact code review run src --scope changed --no-tests
specfact sync bridge --adapter github --mode export-only --repo . --bundle legacy-api
```

These commands are the source of truth. The IDE should support them, not replace them.

## 4. Refresh resources after upgrades

```bash
specfact module upgrade --all
specfact init ide --repo . --ide cursor --force
```

Use `--force` when you intentionally want regenerated editor files to replace the previous export.

## Related

- [Workflows index](/workflows/)
- [Cross-module chains](/guides/cross-module-chains/)
- [Backlog bundle overview](/bundles/backlog/overview/)
