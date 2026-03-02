# specfact-cli-modules
Central module registry for SpecFact CLI marketplace.

## Local development (IDE / Cursor)

Bundle packages import from `specfact_cli` (models, runtime, validators, etc.). Use Hatch so that this repo and your local `specfact-cli` checkout share one dev environment.

1. Create env:

```bash
hatch env create
```

2. Install `specfact-cli` editable dependency:

```bash
# uses $SPECFACT_CLI_REPO if set, otherwise ../specfact-cli
hatch run dev-deps
```

3. In Cursor/VS Code choose interpreter:
`specfact-cli-modules/.venv/bin/python`

## Quality gates

Run this sequence from repo root:

```bash
hatch run format
hatch run type-check
hatch run lint
hatch run yaml-lint
hatch run contract-test
hatch run smart-test
hatch run test
```

Scope notes:
- `ruff` runs on the full repo.
- `basedpyright` and `pylint` are scoped to `src/`, `tests/`, and `tools/` for modules-repo infrastructure parity.
- Bundle-package behavioral validation is covered through `test`, `contract-test`, and migration-specific suite additions under `tests/`.
