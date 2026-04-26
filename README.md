# specfact-cli-modules

Central module registry for SpecFact CLI. This repository hosts official **nold-ai** bundles and their documentation.

## Repository layout

| Path | Purpose |
|------|---------|
| `packages/` | Bundle source packages (one directory per bundle) |
| `registry/` | Published registry index and tarballs |
| `docs/` | Bundle and module documentation (published to GitHub Pages) |
| `scripts/` | CI helpers, signing scripts, quality gates |
| `tests/` | Contract and unit tests for all bundles |
| `openspec/` | OpenSpec change artifacts (proposals, specs, tasks) |

Third-party bundles are published from their own repositories and are not hosted here.

## First-time setup

Prerequisites: Python 3.11+, [Hatch](https://hatch.pypa.io).

```bash
# 1. Create the shared Hatch environment
hatch env create

# 2. Install specfact-cli as an editable dependency
#    (prefers $SPECFACT_CLI_REPO, then a matching worktree branch, then ../specfact-cli)
hatch run dev-deps

# 3. Install pre-commit hooks (runs quality gates and code review on every commit)
pre-commit install
```

In Cursor / VS Code, select the interpreter at `specfact-cli-modules/.venv/bin/python`.

## Quality gates

Run the full gate sequence from the repo root before opening a PR:

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
hatch run specfact code review run --level error --json --out .specfact/code-review.json
```

The pre-commit hooks run the same sequence automatically on every `git commit` (Blocks 1 and 2). To run them manually against all files:

```bash
pre-commit run --all-files
```

### Gate details

- **format / lint / type-check** — Ruff, basedpyright, and pylint. `basedpyright` and `pylint` are scoped to `src/`, `tests/`, and `tools/`; Ruff runs on the full repo.
- **check-bundle-imports** — Enforces import boundary policy (`ALLOWED_IMPORTS.md`). `TYPE_CHECKING`-only imports are excluded from the check.
- **contract-test** — Contract-first test suite; must pass before running `smart-test` / `test`.
- **code review gate** — Runs `specfact code review run --level error` on staged `.py`/`.pyi` files under `packages/`, `registry/`, `scripts/`, `tools/`, `tests/`, and `openspec/changes/`. The pre-commit hook blocks on **error**-severity findings only; warnings are advisory and must be remediated before merge unless a documented exception exists. Full options (`--mode`, `--focus`, `--bug-hunt`, etc.) are documented in [Code review module](./docs/modules/code-review.md).

## Module signatures and versioning

Bump the `version` field in `packages/<bundle>/module-package.yaml` whenever you change a bundle's source payload, then refresh the checksum:

```bash
python scripts/sign-modules.py --allow-unsigned --payload-from-filesystem packages/<bundle>/module-package.yaml
```

The pre-commit hook auto-runs this step and re-stages updated manifests on non-`main` branches.

### When signatures are required

| Context | Requirement |
|---------|------------|
| PRs targeting `dev` | Checksum + version bump; no cryptographic signature required |
| PRs targeting `main` | Cryptographic signature required (`--require-signature`) |
| Push to `dev` / `main` | CI auto-signs via `sign-modules.yml` after merge |
| Approved same-repo PRs | `sign-modules-on-approval.yml` signs before merge using repo secrets |

`registry/index.json` and published tarballs are **not** updated locally — they are updated by `publish-modules` after merge to `dev`/`main`. For rare manual registry repair, use `hatch run sync-registry-from-package --bundle <name>` (not wired into pre-commit).

See [Module signing](./docs/authoring/module-signing.md) for the full signing workflow.

## Documentation

- GitHub Pages: `https://nold-ai.github.io/specfact-cli-modules/`
- URL contract (core → modules handoffs): `docs/reference/documentation-url-contract.md`
