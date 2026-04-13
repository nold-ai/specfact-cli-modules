# CLAUDE.md

This file is an alias surface for Claude Code. Follow [AGENTS.md](AGENTS.md) as the primary bootstrap contract, then load the canonical governance docs in [docs/agent-rules/INDEX.md](docs/agent-rules/INDEX.md).

## Claude-specific note

Claude must treat the canonical rule docs as the source of truth for worktree policy, OpenSpec gating, GitHub completeness checks, TDD order, quality gates, versioning, and documentation rules. Do not rely on this file as a standalone governance handbook.

This modules repository does not use a sibling internal wiki as a required design input. When a change is paired with work in `specfact-cli`, review the paired public change artifacts there before widening scope or redefining shared workflow semantics.

## Clean-code alias

Claude must preserve the clean-code compliance gate and its category references. The canonical review surface enforces `naming`, `kiss`, `yagni`, `dry`, and `solid` and treats clean-code regressions as blocking until they are fixed or explicitly justified.
