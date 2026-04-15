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

**Module signatures:** Split **PR-time** checks from **post-merge branch** checks. **`pr-orchestrator`** (on PRs and related events) runs `verify-modules-signature` with **`--payload-from-filesystem --enforce-version-bump`**, and for pull requests adds **`--version-check-base`**. PRs whose base is **`dev`** use payload checksum + version bump **without** **`--require-signature`**. PRs whose base is **`main`** append **`--require-signature`**; **`push`** paths in that workflow that target **`main`** also append **`--require-signature`**. Separately, **`.github/workflows/sign-modules.yml`** (**Module Signature Hardening**) runs its own verifier: **pushes to `dev` or `main`** execute the **Strict verify** step with **`--require-signature`** (plus **`--payload-from-filesystem --enforce-version-bump`** and **`--version-check-base`** against the push parent); **pull requests** and **`workflow_dispatch`** in that same workflow use **`--payload-from-filesystem --enforce-version-bump`** and **`--version-check-base`** **without** **`--require-signature`** on the head. After merge to **`dev`** or **`main`**, **`sign-modules`** auto-signs (non-bot pushes), strict-verifies on those pushes, and commits without **`[skip ci]`** so follow-up workflows (including **`publish-modules`**) run on the signed tip. Approval-time **`sign-modules-on-approval`** signs with `scripts/sign-modules.py` using **`--payload-from-filesystem`** among other flags; if verification fails after merge, re-sign affected **`module-package.yaml`** files and bump versions as needed. Pre-commit runs `scripts/pre-commit-verify-modules-signature.sh`: **`--require-signature`** only on branch **`main`** or when **`GITHUB_BASE_REF=main`** in Actions; otherwise the same baseline formal verify as PRs to **`dev`**. Refresh checksums locally without a private key via **`python scripts/sign-modules.py --allow-unsigned --payload-from-filesystem`** on changed manifests. On non-`main` branches, the pre-commit hook **auto-runs** that flow (`--changed-only` vs `HEAD`, then vs `HEAD~1` when needed), re-stages updated **`module-package.yaml`** files, and re-verifies. **`registry/index.json`** and published tarballs are **not** updated locally: a manifest may temporarily be **ahead** of `latest_version` until **`publish-modules`** runs on **`dev`**/**`main`** (see **`hatch run yaml-lint`** / `tools/validate_repo_manifests.py`). For rare manual registry repair only, use **`hatch run sync-registry-from-package --bundle`** with a bundle name (for example **`specfact-code-review`**); it is **not** wired into pre-commit so CI publish stays authoritative.

**CI signing:** Approved PRs to `dev` or `main` from **this repository** (not forks) run `.github/workflows/sign-modules-on-approval.yml`, which can commit signed manifests using repository secrets. See [Module signing](./docs/authoring/module-signing.md).

To mirror CI locally with git hooks, enable pre-commit:

```bash
pre-commit install
pre-commit run --all-files
```

**Code review gate (matches specfact-cli core):** runs in **Block 2** after the module verify hook and Block 1 quality hooks (`pre-commit-quality-checks.sh block2`, which calls `scripts/pre_commit_code_review.py`). Staged paths under `packages/`, `registry/`, `scripts/`, `tools/`, `tests/`, and `openspec/changes/` are eligible; `openspec/changes/**/TDD_EVIDENCE.md` is excluded from the gate. Only staged **`.py` / `.pyi`** files are forwarded to SpecFact (YAML, registry tarballs, and similar are skipped). The hook blocks the commit when the JSON report contains **error**-severity findings; warning-only outcomes do not block. Non-blocking warnings reported by SpecFact still require remediation prior to merge unless a documented, approved exception exists. The helper runs `specfact code review run --json --out .specfact/code-review.json` on those Python paths and prints a short findings summary on stderr. Full CLI options (`--mode`, `--focus`, `--level`, `--bug-hunt`, etc.) are documented under [Code review module](./docs/modules/code-review.md). Block 1 is split into separate pre-commit hooks so output appears between stages instead of buffering until the end. Requires a local **specfact-cli** install (`hatch run dev-deps` resolves sibling `../specfact-cli` or `SPECFACT_CLI_REPO`).

Scope notes:
- Pre-commit runs `hatch run lint` in the **Block 1 — lint** hook when any staged path matches `*.py` / `*.pyi`, matching the CI quality job (Ruff alone does not run pylint).
- `ruff` runs on the full repo.
- `basedpyright` and `pylint` are scoped to `src/`, `tests/`, and `tools/` for modules-repo infrastructure parity.
- Bundle-package behavioral validation is covered through `test`, `contract-test`, and migration-specific suite additions under `tests/`.
- `test`, `smart-test`, `contract-test`, `lint`, and `type-check` auto-install the matching local `specfact-cli` editable checkout when the active worktree venv is missing it.
