# AGENTS.md

## Project

`specfact-cli-modules` hosts official nold-ai bundle packages and the module registry used by SpecFact CLI.

## Local setup

```bash
hatch env create
hatch run dev-deps
```

`dev-deps` installs `specfact-cli` from `$SPECFACT_CLI_REPO` when set, otherwise `../specfact-cli`.

## Quality gates

Run in this order:

```bash
hatch run format
hatch run type-check
hatch run lint
hatch run yaml-lint
hatch run contract-test
hatch run smart-test
hatch run test
```

## Scope rules

- Keep bundle package code under `packages/`.
- Keep registry metadata in `registry/index.json` and `packages/*/module-package.yaml`.
- `type-check` and `lint` are scoped to `src/`, `tests/`, and `tools/` for repo tooling quality.
- Use `tests/` for bundle behavior and migration parity tests.
