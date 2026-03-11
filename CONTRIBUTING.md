# Contributing

## Scope

This repository hosts official nold-ai SpecFact bundle packages and registry metadata.

- Official bundles live under `packages/`.
- Registry metadata lives under `registry/index.json` and `packages/*/module-package.yaml`.
- Third-party bundles are not hosted in this repository. Third-party publishers should ship from their own repositories and publish to the registry.

## Local Setup

1. `hatch env create`
2. `hatch run dev-deps`

`dev-deps` resolves `specfact-cli` in this order: `$SPECFACT_CLI_REPO`, matching `specfact-cli-worktrees/<branch>`, then the canonical sibling checkout `../specfact-cli`.

## Quality Gates

Run in this order:

1. `hatch run format`
2. `hatch run type-check`
3. `hatch run lint`
4. `hatch run yaml-lint`
5. `hatch run contract-test`
6. `hatch run smart-test`
7. `hatch run test`

## Pre-Commit

- `pre-commit install`
- `pre-commit run --all-files`
