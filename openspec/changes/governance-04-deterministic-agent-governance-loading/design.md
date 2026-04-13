## Context

**specfact-cli-modules** currently centralizes contributor and agent policy in a single long `AGENTS.md` (quality gates, worktrees, OpenSpec, GitHub cache usage, versioning). That mirrors the pre-migration state of **specfact-cli** and causes the same failure modes: high session token cost, uneven model adherence, and dropped gates after context compaction.

**specfact-cli** addressed this with a compact `AGENTS.md`, `docs/agent-rules/INDEX.md`, machine-readable frontmatter on rule files, explicit GitHub readiness semantics, docs/navigation exposure, and validator/test hooks that make the rule system enforceable ([specfact-cli#494](https://github.com/nold-ai/specfact-cli/issues/494)). This design ports that **pattern** to modules while preserving modules-specific facts: bundle layout under `packages/`, registry in `registry/index.json`, Hatch quality order including **module signature verification**, worktree path convention `../specfact-cli-modules-worktrees/<type>/<slug>` resolved from the repository parent (`REPO_ROOT/..`, i.e. the directory that contains the primary clone—avoid collapsing or confusing that parent with a different sibling checkout), and Jekyll docs under `docs/` with permalink contracts.

The hierarchy cache capability ([specfact-cli-modules#178](https://github.com/nold-ai/specfact-cli-modules/issues/178)) already exists; this change only extends it so **bootstrap** treats cache refresh as mandatory when freshness rules fire—not an optional footnote.

## Goals / Non-Goals

**Goals:**

- Deterministic session bootstrap: `AGENTS.md` → index → non-negotiable checklist → applicability-selected rules.
- Frontmatter on every `docs/agent-rules/*.md` file that governs agents, with schema fields aligned to the specfact-cli implementation so cross-repo tooling can converge later.
- Explicit precedence among `AGENTS.md`, index, rule files, change-local OpenSpec artifacts, and explicit user override where policy allows.
- Public GitHub issue readiness: parent (cache-backed), labels, project, blockers, blocked-by, and **`in progress` concurrency stop**.
- Session bootstrap **must** refresh `.specfact/backlog/github_hierarchy_cache.md` when missing or stale before hierarchy-dependent work.
- Port the concrete validator/test surfaces that enforce the model in `specfact-cli`: rule-index/checklist existence checks, agent-rule frontmatter validation, canonical `applies_when` signal validation, and docs exposure through navigation/frontmatter contracts.
- Close remaining hierarchy-cache drift that would undermine deterministic bootstrap, specifically repo-aware state reuse and user-facing CLI error handling.

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

Add or extend automated checks (pytest or existing doc-lint) so required frontmatter keys, always-load files, canonical `applies_when` signals, and index references stay enforced—mirroring specfact-cli’s “governance docs are contractually testable” approach.

**Open placement:** Either extend an existing markdown/frontmatter test harness or add a focused `tests/unit/test_agent_governance_rules.py` (final choice in implementation).

### Decision: `openspec/config.yaml` stays authoritative for artifact rules

After migration, ensure `proposal`/`tasks` rules in `openspec/config.yaml` **reference** canonical rule files for narrative policy instead of duplicating long passages—while keeping concrete modules constraints (signatures, registry, backlog cache script) in config where they are artifact-scoped injection.

### Decision: Follow the same alias-surface pattern as `specfact-cli`

Mirror the core repo's compact alias strategy for tool-specific instruction files:

- `CLAUDE.md` remains a short alias that points to `AGENTS.md` and `docs/agent-rules/INDEX.md`
- `.cursorrules` becomes a Cursor-facing alias surface that points to the same canonical governance sources instead of redefining the workflow independently
- `.github/copilot-instructions.md` is added as a similarly compact alias for Copilot/GitHub surfaces

Modules should adapt the reminder bullets to repository-specific facts (module signing, worktree path, cache script, docs site) but keep the **alias, not handbook** pattern used in `specfact-cli`.

### Decision: Include cache-script hardenings in the same governance parity change

Deterministic bootstrap now depends on `.specfact/backlog/github_hierarchy_cache.md` being both fresh and trustworthy. The modules copy of `scripts/sync_github_hierarchy_cache.py` predates later core hardenings around repo-aware state reuse and CLI error reporting. This change therefore includes those script/test alignments so the governance rule system does not depend on a weaker cache implementation.

**Alternatives:** Track those script fixes in a separate follow-up to `governance-03-github-hierarchy-cache` → rejected (keeps the bootstrap parity change conceptually incomplete and leaves the modules flow behind the improved core behavior).

## Risks / Trade-offs

- [Rule sprawl] → Mitigate with bounded always-load set and automated schema checks.
- [Drift from specfact-cli semantics] → Mitigate by pairing with [specfact-cli#494](https://github.com/nold-ai/specfact-cli/issues/494) and cross-linking in proposal/CHANGE_ORDER.
- [Contributors skip the index] → Mitigate with explicit repetition in compact `AGENTS.md`.
- [False confidence if `gh` metadata stale] → Mitigate with live checks and explicit stop on `in progress` ambiguity per rule text.
- [Docs migration lands without enforcement] → Mitigate by porting the validator/test hooks and docs navigation surfaces together, not as implied later cleanup.
- [Bootstrap relies on stale cache state semantics] → Mitigate by aligning the modules cache script/tests with the current core behavior in the same change.

## Migration Plan

1. Land spec deltas and failing tests for frontmatter/index invariants, canonical task-signal validation, and cache-bootstrap wording.
2. Add `docs/agent-rules/**`, update docs navigation/schema references, and shrink `AGENTS.md`.
3. Update thin aliases (`CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`) and `openspec/config.yaml` cross-references.
4. Extend `github-hierarchy-cache` behavior in docs + spec via MODIFIED delta; implement bootstrap wording, GitHub-readiness rule text, and cache-script hardenings/tests.
5. Run quality gates; refresh `TDD_EVIDENCE.md`; add `openspec/CHANGE_ORDER.md` row for `governance-04`.
6. PR to `dev`; after merge, archive via `openspec archive governance-04-deterministic-agent-governance-loading`.

## Open Questions

- Whether to share a single frontmatter JSON Schema with specfact-cli via a future extracted package, or duplicate schema/constants in both repos until then.
