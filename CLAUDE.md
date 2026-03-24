# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`specfact-cli-modules` hosts official nold-ai bundle packages and the module registry used by SpecFact CLI. Bundle packages import from `specfact_cli` (models, runtime, validators). The core CLI lives in a sibling repo (`specfact-cli`).

## Local Setup

```bash
hatch env create
hatch run dev-deps   # installs specfact-cli from $SPECFACT_CLI_REPO or ../specfact-cli
```

In worktrees, `dev-deps` prefers a matching `specfact-cli-worktrees/<branch>` checkout before falling back to the canonical sibling repo.

## Quality Gates

Run in this order:

```bash
hatch run format
hatch run type-check
hatch run lint
hatch run yaml-lint
hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump
hatch run contract-test
hatch run smart-test
hatch run test
```

Run a single test file: `hatch run test tests/path/to/test_file.py`
Run a single test: `hatch run test tests/path/to/test_file.py::TestClass::test_name`

Pre-commit hooks mirror CI: `pre-commit install && pre-commit run --all-files`

CI runs in `.github/workflows/pr-orchestrator.yml` — matrix quality gates on Python 3.11/3.12/3.13.

## Architecture

### Bundle packages (`packages/<bundle-name>/`)

Six official bundles: `specfact-backlog`, `specfact-codebase`, `specfact-code-review`, `specfact-govern`, `specfact-project`, `specfact-spec`. Each bundle has:
- `module-package.yaml` — name, version, commands, core_compatibility, integrity checksums
- `src/<python_package>/` — bundle source code

### Import policy (`ALLOWED_IMPORTS.md`)

- Only allowed `specfact_cli.*` prefixes may be imported in bundle code (CORE/SHARED APIs only)
- Cross-bundle lateral imports are forbidden except specific allowed pairs (e.g. `specfact_spec` -> `specfact_project`)
- Enforced by `hatch run check-bundle-imports`

### Registry (`registry/`)

- `index.json` — published bundle metadata (versions, artifact URLs, checksums)
- `modules/` and `signatures/` — published artifacts

### Repo tooling

- `tools/` — development infrastructure (type-checker wrapper, smart test coverage, contract-first testing, manifest validation, core dependency bootstrapping)
- `scripts/` — publishing, signing, import checking, pre-commit hooks
- `src/specfact_cli_modules/` — shared repo-level Python package

### OpenSpec workflow (`openspec/`)

- `openspec/specs/` — canonical specifications
- `openspec/changes/` — active change proposals (proposal, design, delta specs, tasks, TDD evidence)
- `openspec/changes/archive/` — completed changes
- `openspec/CHANGE_ORDER.md` — tracks change sequencing and dependencies

## Development Workflow

### Branch protection

`dev` and `main` are protected — never work directly on them. Use feature branches: `feature/*`, `bugfix/*`, `hotfix/*`, `chore/*`. PRs go to `dev` unless release workflow requires `main`.

### Git worktrees

Use worktrees for parallel branch work. Keep primary checkout as canonical `dev` workspace. Worktree paths: `../specfact-cli-modules-worktrees/<branch-type>/<branch-slug>`.

### OpenSpec (required before code changes)

Verify an active OpenSpec change covers the requested scope before changing code. If missing: create or extend a change first.

Follow strict TDD order: spec delta -> failing tests -> implementation -> passing tests -> quality gates. Record TDD evidence in `openspec/changes/<change-id>/TDD_EVIDENCE.md`.

### OpenSpec archive rule (hard requirement)

Never manually move folders under `openspec/changes/` into `archive/`. Archiving MUST use `openspec archive <change-id>` (or equivalent workflow command). Update `openspec/CHANGE_ORDER.md` when archive status changes.

## Bundle Versioning

SemVer: patch (bug fix), minor (new command/option/API), major (breaking change/removal). When bumping a version, review and update `core_compatibility` in both `module-package.yaml` and `registry/index.json`.

## Linting Scope

- `ruff` runs on the full repo
- `basedpyright` and `pylint` are scoped to `src/`, `tests/`, and `tools/`
- Line length: 120 characters
- Python target: 3.11+
