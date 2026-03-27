---
layout: default
title: CI/CD Pipeline
permalink: /guides/ci-cd-pipeline/
---

# CI/CD Pipeline

This guide maps the repository quality gates to a workflow you can run locally and in GitHub Actions.

## 1. Keep local resources aligned

When workflow prompts or templates are bundle-owned, refresh the IDE export after module changes:

```bash
specfact init ide --repo . --ide cursor --force
```

Install the repository hooks locally so the same guardrails run before you push:

```bash
pre-commit install
pre-commit run --all-files
```

## 2. Run the repository quality gates locally

The repository gate order is:

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

Use the same order locally before pushing changes that affect docs, bundles, or registry metadata.

## 2.1 CI/CD stage mapping

Map the local commands to the pipeline stages this repository enforces:

- Pre-commit stage: `pre-commit run --all-files`
- Quality gates stage: `hatch run format` -> `hatch run type-check` -> `hatch run lint` -> `hatch run yaml-lint`
- Release-readiness stage: `hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`
- Validation stage: `hatch run contract-test` -> `hatch run smart-test` -> `hatch run test`

## 3. Add scoped workflow checks while developing

```bash
specfact code review run docs/guides/cross-module-chains.md --no-tests
specfact govern enforce sdd legacy-api --no-interactive
```

These commands complement the repository gates when your branch specifically changes workflow docs or bundle enforcement behavior.

## 4. Build the docs site before publishing

```bash
bundle exec jekyll build --destination ../_site
```

Run this when you changed published documentation so link, redirect, and front-matter issues are caught before PR review.

## Related

- [Workflows index](/workflows/)
- [Command reference](/reference/commands/)
- [Cross-module chains](/guides/cross-module-chains/)
