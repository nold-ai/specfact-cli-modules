---
layout: default
title: Brownfield Modernization
permalink: /guides/brownfield-modernization/
keywords: [brownfield, modernization, legacy, migration, code]
audience: [solo, team]
expertise_level: [intermediate]
---

# Brownfield Modernization

This guide consolidates the previous brownfield engineer and journey pages into one current flow based on the command surface that ships in this repository.

## 1. Prepare the repository and installed resources

```bash
specfact init --profile solo-developer
specfact init ide --repo . --ide cursor
```

The IDE bootstrap matters because backlog refinement, review prompts, and other workflow resources are bundle-owned payloads. Do not rely on legacy prompt files outside the installed modules.

## 2. Import the legacy codebase into a project bundle

```bash
specfact code import legacy-api --repo .
```

This creates or refreshes the project bundle that the later workflow stages use.

## 3. Analyze contract and validation coverage

```bash
specfact code analyze contracts --repo . --bundle legacy-api
```

Use this to identify where the codebase already has contract signals and where modernization work still needs enforcement.

## 4. Sync or export project state when outside tools are involved

```bash
specfact sync bridge --adapter github --mode export-only --repo . --bundle legacy-api
```

Use the bridge layer when you need to exchange bundle state with GitHub, Azure DevOps, OpenSpec, or another supported adapter.

## 5. Validate the extracted or maintained contracts

```bash
specfact spec validate --bundle legacy-api --force
```

If you are working from a single contract file instead of a bundle, validate that file directly with `specfact spec validate api/openapi.yaml`.

## 6. Enforce readiness before promotion

```bash
specfact govern enforce sdd legacy-api --no-interactive
```

Run this before promotion or release to ensure the bundle, manifest, and contract state still agree.

## Suggested cadence

1. Import and analyze first.
2. Add or refine contracts where the analysis shows gaps.
3. Validate contracts after every meaningful refactor.
4. Use bridge sync only when external tools must stay aligned.
5. Run SDD enforcement before promotion, release, or handoff.

## Related

- [Brownfield FAQ and ROI](/guides/brownfield-faq-and-roi/)
- [Brownfield examples](/guides/brownfield-examples/)
- [Codebase bundle overview](/bundles/codebase/overview/)
