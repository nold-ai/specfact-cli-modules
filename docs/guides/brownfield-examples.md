---
layout: default
title: Brownfield Examples
permalink: /guides/brownfield-examples/
---

# Brownfield Examples

These examples give you three concrete modernization patterns you can adapt without relying on the removed legacy `docs/examples` tree.

## Example 1. Legacy API intake

Use this when an undocumented repository needs a bundle baseline before any release work:

```bash
specfact code import legacy-api --repo .
specfact code analyze contracts --repo . --bundle legacy-api
specfact spec validate --bundle legacy-api
```

Outcome: the team gets a project bundle, contract visibility, and an initial validation pass.

## Example 2. Backlog to modernization handoff

Use this when backlog items must be refined before the modernization work is synchronized or exported:

```bash
specfact backlog ceremony refinement github --preview --labels feature
specfact backlog verify-readiness --adapter github --project-id owner/repo --target-items 123
specfact project sync bridge --adapter github --mode export-only --repo . --bundle legacy-api
```

Outcome: backlog items are standardized before they drive bundle changes.

## Example 3. Promotion gate for a risky refactor

Use this when a refactor changed contracts or bundle state and you need a release gate:

```bash
specfact spec backward-compat api/openapi.yaml --previous api/openapi.v1.yaml
specfact spec generate-tests api/openapi.yaml
specfact govern enforce sdd legacy-api --no-interactive
```

Outcome: compatibility, generated test artifacts, and bundle enforcement are checked in one flow.

## Related

- [Brownfield modernization](/guides/brownfield-modernization/)
- [Cross-module chains](/guides/cross-module-chains/)
- [Contract testing workflow](/guides/contract-testing-workflow/)
