# GitHub Copilot Instructions — specfact-cli-modules

Use [AGENTS.md](../AGENTS.md) as the mandatory bootstrap surface and [docs/agent-rules/INDEX.md](../docs/agent-rules/INDEX.md) as the canonical governance dispatcher.

## Minimal reminders

- Work belongs on `feature/*`, `bugfix/*`, `hotfix/*`, or `chore/*` branches, normally in a worktree rooted under `../specfact-cli-modules-worktrees/`.
- Refresh `.specfact/backlog/github_hierarchy_cache.md` with `python scripts/sync_github_hierarchy_cache.py` when GitHub hierarchy metadata is missing or stale before parent or blocker work.
- This repository enforces the clean-code review gate through `hatch run specfact code review run --json --out .specfact/code-review.json`.
- Signed module or manifest changes require version-bump review and `verify-modules-signature`.
- The full governance rules live in `docs/agent-rules/`; do not treat this file as a complete standalone handbook.
