## Context

**specfact-cli-modules** currently centralizes contributor and agent policy in a single long `AGENTS.md` (quality gates, worktrees, OpenSpec, GitHub cache usage, versioning). That mirrors the pre-migration state of **specfact-cli** and causes the same failure modes: high session token cost, uneven model adherence, and dropped gates after context compaction.

**specfact-cli** addressed this with a compact `AGENTS.md`, `docs/agent-rules/INDEX.md`, machine-readable frontmatter on rule files, and explicit GitHub readiness semantics ([specfact-cli#494](https://github.com/nold-ai/specfact-cli/issues/494)). This design ports that **pattern** to modules while preserving modules-specific facts: bundle layout under `packages/`, registry in `registry/index.json`, Hatch quality order including **module signature verification**, worktree path convention `../specfact-cli-modules-worktrees/<type>/<slug>`, and Jekyll docs under `docs/` with permalink contracts.

The hierarchy cache capability ([specfact-cli-modules#178](https://github.com/nold-ai/specfact-cli-modules/issues/178)) already exists; this change only extends it so **bootstrap** treats cache refresh as mandatory when freshness rules fire—not an optional footnote.

## Goals / Non-Goals

**Goals:**

- Deterministic session bootstrap: `AGENTS.md` → index → non-negotiable checklist → applicability-selected rules.
- Frontmatter on every `docs/agent-rules/*.md` file that governs agents, with schema fields aligned to the specfact-cli implementation so cross-repo tooling can converge later.
- Explicit precedence among `AGENTS.md`, index, rule files, change-local OpenSpec artifacts, and explicit user override where policy allows.
- Public GitHub issue readiness: parent (cache-backed), labels, project, blockers, blocked-by, and **`in progress` concurrency stop**.
- Session bootstrap **must** refresh `.specfact/backlog/github_hierarchy_cache.md` when missing or stale before hierarchy-dependent work.

**Non-Goals:**

- Replacing OpenSpec CLI lifecycle or inventing a new policy engine.
- Changing bundle runtime behavior or registry wire-up (unless a small validator is added under `tests/` / `tools/`).
- Duplicating specfact-cli’s internal wiki rules; modules has no sibling internal wiki requirement in this change.

## Decisions

### Decision: Mirror specfact-cli file layout and semantics

Use the same structural anchors as specfact-cli: `docs/agent-rules/INDEX.md`, `05-non-negotiable-checklist.md`, and numbered domain files (`10-session-bootstrap.md`, `20-repository-context.md`, `30-worktrees-and-branching.md`, `40-openspec-and-tdd.md`, `50-quality-gates-and-review.md`, `60-github-change-governance.md`, `70-release-commit-and-docs.md`, `80-current-guidance-catalog.md`) with content **adapted** to modules paths, Hatch commands, signature verification, and modules GitHub hierarchy cache script (`python scripts/sync_github_hierarchy_cache.py`).

**Alternatives:** Invent a modules-only naming scheme → rejected (fragments cross-repo mental model and future shared validators).

### Decision: Keep `AGENTS.md` as mandatory first read

Retain compatibility with tools that prioritize `AGENTS.md`; shrink it to bootstrap + precedence + pointers only.

### Decision: Validation lives in repo tests

Add or extend automated checks (pytest or existing doc-lint) so required frontmatter keys, always-load files, and index references stay enforced—mirroring specfact-cli’s “governance docs are contractually testable” approach.

**Open placement:** Either extend an existing markdown/frontmatter test harness or add a focused `tests/unit/test_agent_governance_rules.py` (final choice in implementation).

### Decision: `openspec/config.yaml` stays authoritative for artifact rules

After migration, ensure `proposal`/`tasks` rules in `openspec/config.yaml` **reference** canonical rule files for narrative policy instead of duplicating long passages—while keeping concrete modules constraints (signatures, registry, backlog cache script) in config where they are artifact-scoped injection.

## Risks / Trade-offs

- [Rule sprawl] → Mitigate with bounded always-load set and automated schema checks.
- [Drift from specfact-cli semantics] → Mitigate by pairing with [specfact-cli#494](https://github.com/nold-ai/specfact-cli/issues/494) and cross-linking in proposal/CHANGE_ORDER.
- [Contributors skip the index] → Mitigate with explicit repetition in compact `AGENTS.md`.
- [False confidence if `gh` metadata stale] → Mitigate with live checks and explicit stop on `in progress` ambiguity per rule text.

## Migration Plan

1. Land spec deltas and failing tests for frontmatter/index invariants.
2. Add `docs/agent-rules/**` and shrink `AGENTS.md`.
3. Update thin aliases (`CLAUDE.md` if present) and `openspec/config.yaml` cross-references.
4. Extend `github-hierarchy-cache` behavior in docs + spec via MODIFIED delta; implement bootstrap wording and any validator hooks.
5. Run quality gates; refresh `TDD_EVIDENCE.md`; add `openspec/CHANGE_ORDER.md` row for `governance-04`.
6. PR to `dev`; after merge, archive via `openspec archive governance-04-deterministic-agent-governance-loading`.

## Open Questions

- Whether to share a single frontmatter JSON Schema with specfact-cli via a future extracted package, or duplicate schema constants in both repos until then.
- Whether `.cursorrules` / Cursor-specific rules should point only at `AGENTS.md` or also at `docs/agent-rules/INDEX.md` for dual-tool parity.
