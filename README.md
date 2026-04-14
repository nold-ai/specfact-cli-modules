# specfact-cli-modules
Central module registry for SpecFact CLI marketplace.

## Repository scope

This repository hosts official nold-ai bundles only.

- Official bundles are maintained under `packages/`.
- Third-party bundles are published from third-party repositories and are not hosted here.
- Bundle and module documentation changes are made in this repository under `docs/`.
- Cross-site linking rules and canonical paths for core→modules handoffs: `docs/reference/documentation-url-contract.md` (published: `https://modules.specfact.io/reference/documentation-url-contract/`).
- GitHub Pages documentation target: `https://nold-ai.github.io/specfact-cli-modules/`.

## Local development (IDE / Cursor)

Bundle packages import from `specfact_cli` (models, runtime, validators, etc.). Use Hatch so that this repo and your local `specfact-cli` checkout share one dev environment.

1. Create env:

```bash
hatch env create
```

2. Install `specfact-cli` editable dependency:

```bash
# prefers $SPECFACT_CLI_REPO, then a matching specfact-cli-worktrees branch, then ../specfact-cli
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
hatch run check-bundle-imports
hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump
hatch run contract-test
hatch run smart-test
hatch run test
hatch run specfact code review run --json --out .specfact/code-review.json
```

**Module signatures:** `pr-orchestrator` enforces `--require-signature` only for events targeting **`main`**; for **`dev`** (and feature branches) CI checks checksums and version bumps without requiring a cryptographic signature yet. Add `--require-signature` to the `verify-modules-signature` command when you want the same bar as **`main`** (for example before merging to `main`). Pre-commit runs `scripts/pre-commit-verify-modules-signature.sh`, which mirrors that policy (signatures required on branch `main`, or when `GITHUB_BASE_REF=main` in Actions).

**CI signing:** Approved PRs to `dev` or `main` from **this repository** (not forks) run `.github/workflows/sign-modules-on-approval.yml`, which can commit signed manifests using repository secrets. See [Module signing](./docs/authoring/module-signing.md).

To mirror CI locally with git hooks, enable pre-commit:

```bash
pre-commit install
pre-commit run --all-files
```

**Code review gate (matches specfact-cli core):** runs in **Block 2** after the module verify hook and Block 1 quality hooks (`pre-commit-quality-checks.sh block2`, which calls `scripts/pre_commit_code_review.py`). Staged paths under `packages/`, `registry/`, `scripts/`, `tools/`, `tests/`, and `openspec/changes/` are eligible; `openspec/changes/**/TDD_EVIDENCE.md` is excluded from the gate. OpenSpec Markdown other than evidence files is not passed to SpecFact (the review CLI treats paths as Python). The helper runs `specfact code review run --json --out .specfact/code-review.json` on the remaining paths and prints only a short findings summary and copy-paste prompts on stderr. Block 1 is split into separate pre-commit hooks so output appears between stages instead of buffering until the end. Requires a local **specfact-cli** install (`hatch run dev-deps` resolves sibling `../specfact-cli` or `SPECFACT_CLI_REPO`).

Scope notes:
- Pre-commit runs `hatch run lint` in the **Block 1 — lint** hook when any staged path matches `*.py` / `*.pyi`, matching the CI quality job (Ruff alone does not run pylint).
- `ruff` runs on the full repo.
- `basedpyright` and `pylint` are scoped to `src/`, `tests/`, and `tools/` for modules-repo infrastructure parity.
- Bundle-package behavioral validation is covered through `test`, `contract-test`, and migration-specific suite additions under `tests/`.
- `test`, `smart-test`, `contract-test`, `lint`, and `type-check` auto-install the matching local `specfact-cli` editable checkout when the active worktree venv is missing it.
