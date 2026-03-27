---
layout: default
title: Spec bundle overview
nav_order: 2
permalink: /bundles/spec/overview/
---

# Spec bundle overview

The **Spec** bundle (`nold-ai/specfact-spec`) mounts under the **`specfact spec`** command group. That group exposes **Specmatic-backed contract validation** commands, **SDD** manifest utilities, and **generate** workflows for contracts and prompts.

Install the bundle, then confirm the mounted tree with `specfact spec --help`.

## Prerequisites

- `specfact module install nold-ai/specfact-spec`
- Optional tooling per workflow (Specmatic, OpenAPI files, etc.)

## `specfact spec` — Specmatic commands

| Command | Purpose |
|--------|---------|
| `validate` | Validate OpenAPI/AsyncAPI specs via Specmatic |
| `backward-compat` | Compare two spec versions for compatibility |
| `generate-tests` | Generate Specmatic test suites |
| `mock` | Run a Specmatic mock server |

## `specfact spec sdd` — SDD manifests

| Command | Purpose |
|--------|---------|
| `list` | List SDD manifests in the repo |

### `constitution` subcommands

| Subcommand | Purpose |
|------------|---------|
| `bootstrap` | Bootstrap constitution markdown for Spec-Kit compatibility |
| `enrich` | Enrich constitution content |
| `validate` | Validate constitution structure |

## `specfact spec generate` — generation and prompts

| Command | Purpose |
|--------|---------|
| `contracts` | Generate contract artifacts from plans |
| `contracts-prompt` | Emit prompts for contract work |
| `contracts-apply` | Apply generated contract changes |
| `fix-prompt` | Prompt-driven fix flows |
| `test-prompt` | Prompt-driven test flows |

## Bundle-owned prompts

Generate and contract flows emit **prompts** shipped with the bundle. They are **bundle resources**, not core CLI files. Use `specfact init ide` to refresh IDE exports after bundle upgrades.

## Quick examples

```bash
specfact spec --help
specfact spec validate --help
specfact spec backward-compat --help
specfact spec generate-tests --help
specfact spec mock --help
specfact spec sdd list --repo .
specfact spec sdd constitution validate --help
specfact spec generate contracts --help
```

## See also

- [Command reference](../../reference/commands/) — bundle-to-command mapping
- [Spec validate and backward compatibility](/bundles/spec/validate/)
- [Generate Specmatic tests](/bundles/spec/generate-tests/)
- [Run a mock server](/bundles/spec/mock/)
- [Contract testing workflow](../../guides/contract-testing-workflow/)
