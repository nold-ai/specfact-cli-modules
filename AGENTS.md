# AGENTS.md

## Project

`specfact-cli-modules` hosts official nold-ai bundle packages and the module registry used by SpecFact CLI.

## Local setup

```bash
hatch env create
hatch run dev-deps
```

`dev-deps` installs `specfact-cli` from `$SPECFACT_CLI_REPO` when set, otherwise `../specfact-cli`.
In worktrees, the bootstrap should prefer the matching `specfact-cli-worktrees/<branch>` checkout before falling back to the canonical sibling repo.

## Quality gates

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

# SpecFact code review JSON (dogfood; see "SpecFact Code Review JSON" below and openspec/config.yaml)
hatch run specfact code review run --json --out .specfact/code-review.json
```

CI orchestration runs in `.github/workflows/pr-orchestrator.yml` and enforces:
- module signature + version-bump verification
- matrix quality gates on Python 3.11/3.12/3.13

## Pre-commit (local)

Install and run pre-commit hooks so they mirror the CI quality gates:

```bash
pre-commit install
pre-commit run --all-files
```

Hooks run in order: **module signature verification** → **`scripts/pre-commit-quality-checks.sh`** (includes `hatch run lint` / pylint for staged Python) → **`scripts/pre_commit_code_review.py`** (SpecFact code review gate writing `.specfact/code-review.json`). That last hook is fast feedback on staged `*.py` / `*.pyi` files; it does not replace the **PR / change-completion** review rules in the next section when OpenSpec tasks require a full-scope run.

## SpecFact Code Review JSON (Dogfood, Quality Gate)

This matches **`openspec/config.yaml`** (project `context` and **`rules.tasks`** for code review): treat **`.specfact/code-review.json`** as mandatory evidence before an OpenSpec change is considered complete and before you rely on “all gates green” for a PR. Requires a working **specfact-cli** install (`hatch run dev-deps`).

**When to (re)run the review**

- The file is **missing**, or
- It is **stale**: the report’s last-modified time is older than any file you changed for this work under `packages/`, `registry/`, `scripts/`, `tools/`, `tests/`, or under `openspec/changes/<change-id>/` **except** `openspec/changes/<change-id>/TDD_EVIDENCE.md` — evidence-only edits there do **not** by themselves invalidate the review; re-run when proposal, specs, tasks, design, or code change.

**Command**

```bash
hatch run specfact code review run --json --out .specfact/code-review.json
```

- While iterating on a branch, prefer a **changed-files scope** when available (e.g. `--scope changed`) so feedback stays fast.
- Before the **final PR** for a change, run a **full** (or equivalent) scope so the report covers the whole quality surface your tasks expect (e.g. `--scope full`).

**Remediation**

- Read the JSON report and fix **every** finding at any severity (warning, advisory, error, or equivalent in the schema) unless the change proposal documents a **rare, explicit, justified** exception.
- After substantive edits, re-run until the report shows a **passing** outcome from the review module (e.g. overall verdict PASS / CI exit 0 per schema).
- Record the review command(s) and timestamp in `openspec/changes/<change-id>/TDD_EVIDENCE.md` or in the PR description when the change touches behavior or quality gates.

**Consistency**

- OpenSpec change **`tasks.md`** should include explicit tasks for generating/updating this file and clearing findings (see `openspec/config.yaml` → `rules.tasks` → “SpecFact code review JSON”). Agent runs should treat those tasks and this section as the same bar.

## Development workflow

### Branch protection

`dev` and `main` are protected. Never work directly on them.

- Use feature branches for implementation: `feature/*`, `bugfix/*`, `hotfix/*`, `chore/*`
- Open PRs to `dev` (or to `main` only when explicitly required by release workflow)

### Git worktree policy

Use worktrees for parallel branch work.

- Allowed branch types in worktrees: `feature/*`, `bugfix/*`, `hotfix/*`, `chore/*`
- Forbidden in worktrees: `dev`, `main`
- Keep primary checkout as canonical `dev` workspace
- Keep worktree paths under `../specfact-cli-modules-worktrees/<branch-type>/<branch-slug>`

Recommended create/list/cleanup:

```bash
git fetch origin
git worktree add ../specfact-cli-modules-worktrees/feature/<branch-slug> -b feature/<branch-slug> origin/dev
git worktree list
git worktree remove ../specfact-cli-modules-worktrees/feature/<branch-slug>
```

### OpenSpec workflow (required)

Before changing code, verify an active OpenSpec change explicitly covers the requested scope.

- If missing scope: create or extend a change first (`openspec` workflow)
- Follow strict TDD order: spec delta -> failing tests -> implementation -> passing tests -> quality gates
- Record failing/passing evidence in `openspec/changes/<change-id>/TDD_EVIDENCE.md`
- For GitHub issue setup, parent linking, or blocker lookup, consult `.specfact/backlog/github_hierarchy_cache.md` first. This cache is ephemeral local state and MUST NOT be committed.
- Rerun `python scripts/sync_github_hierarchy_cache.py` whenever the cache is missing or stale, and recreate it as part of OpenSpec and GitHub issue work.

### OpenSpec archive rule (hard requirement)

Do not manually move folders under `openspec/changes/` into `openspec/changes/archive/`.

- Archiving MUST be done with `openspec archive <change-id>` (or equivalent workflow command that wraps it)
- Use the default archive behavior that syncs specs/deltas as part of archive
- Update `openspec/CHANGE_ORDER.md` in the same change when archive status changes

## Scope rules

- Keep bundle package code under `packages/`.
- Keep registry metadata in `registry/index.json` and `packages/*/module-package.yaml`.
- `type-check` and `lint` are scoped to `src/`, `tests/`, and `tools/` for repo tooling quality.
- Use `tests/` for bundle behavior and migration parity tests.
- This repository hosts official nold-ai bundles only; third-party bundles publish from their own repositories.

## Bundle versioning policy

### SemVer rules

- `patch`: bug fix with no command/API change
- `minor`: new command, option, or public API addition
- `major`: breaking API/behavior change or command removal

### core_compatibility rules

- When a bundle requires a newer minimum `specfact-cli`, update `core_compatibility` in:
  - `packages/<bundle>/module-package.yaml`
  - `registry/index.json` entry metadata (when field is carried there)
- Treat `core_compatibility` review as mandatory on each version bump.

### Release process

1. Branch from `origin/dev` into a feature/hotfix branch.
2. Bump bundle version in `packages/<bundle>/module-package.yaml`.
3. Run publish pre-check:
   - `python scripts/publish-module.py --bundle <bundle>`
4. Publish with project tooling (`scripts/publish-module.py --bundle <name>` wrapper + packaging flow).
5. Update `registry/index.json` with new `latest_version`, artifact URL, and checksum.
6. Tag release and merge via PR after quality gates pass.
