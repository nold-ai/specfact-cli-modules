---
layout: default
title: Contract Testing Workflow
permalink: /contract-testing-workflow/
redirect_from:
  - /guides/contract-testing-workflow/
---

# Contract Testing Workflow

This workflow uses the current `specfact spec` command group for Specmatic-backed validation and mock flows.

## 1. Validate the current contract

```bash
specfact spec validate api/openapi.yaml
```

Use `--bundle <name>` when you want to validate all contracts attached to a project bundle instead of a single file.

## 2. Check backward compatibility before release

```bash
specfact spec backward-compat api/openapi.yaml --previous api/openapi.v1.yaml
```

Run this before publishing a changed contract or promoting a release candidate.

## 3. Generate test suites from the spec

```bash
specfact spec generate-tests api/openapi.yaml
```

This is the fastest way to turn a validated contract into executable Specmatic coverage.

## 4. Start a mock server for integration testing

```bash
specfact spec mock api/openapi.yaml
```

Use the mock server when downstream services or frontend integrations need a stable contract target before the real implementation is ready.

## 5. Gate the release bundle

```bash
specfact govern enforce sdd legacy-api --no-interactive
```

This ties contract validation back into release readiness for the bundle that owns the API.

## Related

- [Spec bundle overview](/bundles/spec/overview/)
- [Govern enforce](/bundles/govern/enforce/)
- [Cross-module chains](/guides/cross-module-chains/)
