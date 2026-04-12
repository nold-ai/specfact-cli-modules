## Why

`AGENTS.md` in **specfact-cli-modules** mixes bootstrap policy, quality gates, and long-form workflow detail in one surface. That raises token cost for every session and makes cross-model behavior less deterministic around worktrees, OpenSpec, cache-first GitHub hierarchy, TDD, and PR completion gates. This change aligns the modules repo with the **deterministic agent-governance** model already shipped in **specfact-cli** ([specfact-cli#494](https://github.com/nold-ai/specfact-cli/issues/494)) so both repositories share the same loading semantics and stop conditions.

## What Changes

- Introduce a **compact** root `AGENTS.md` that only holds the mandatory bootstrap contract and points at canonical rule artifacts under `docs/agent-rules/`.
- Add **`docs/agent-rules/INDEX.md`** as the dispatcher for applicability-based rule loading, always-load subset, precedence, and stop/continue semantics.
- Add **`docs/agent-rules/05-non-negotiable-checklist.md`** and focused domain rule files (bootstrap, worktrees, OpenSpec/TDD, quality gates, GitHub change governance, release/docs) with **YAML frontmatter** (`id`, `always_load`, `applies_when`, `priority`, `blocking`, `user_interaction_required`, `stop_conditions`, `depends_on`, etc.).
- Extend **cache-first** guidance so session bootstrap **refreshes** `.specfact/backlog/github_hierarchy_cache.md` when missing or stale before hierarchy-dependent GitHub work.
- Make **GitHub metadata completeness** and **`in progress` ambiguity** explicit readiness gates for public tracked work (parent, labels, project, blockers, blocked-by, live state).
- Port the **validator and docs-contract surfaces** that make the sister-repo flow deterministic in practice: rule-frontmatter validation, canonical `applies_when` signal validation, rule index/checklist tests, and contributor docs/navigation for the new governance layout.
- Update **`openspec/config.yaml`**, **`openspec/CHANGE_ORDER.md`**, docs navigation, and thin alias surfaces (`CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md` where applicable) so OpenSpec artifact rules and contributor guidance reference the canonical rule system instead of duplicating the full handbook.
- Bring the modules **hierarchy-cache implementation** up to the current parity bar needed by deterministic bootstrap: repo-aware state matching, normalized cache-governance spec text, and clear CLI error reporting/tests.

## Capabilities

### New Capabilities

- `agent-governance-loading`: Deterministic bootstrap, rule discovery, rule frontmatter, precedence, and stop-condition behavior for AI instruction surfaces in this repository.

### Modified Capabilities

- `github-hierarchy-cache`: Require session-bootstrap refresh of the local hierarchy cache when it is missing or stale, as part of the compact governance flow (delta on top of existing cache-first lookup requirements).

## Impact

- **Documentation and instruction surfaces**: `AGENTS.md`, new `docs/agent-rules/**`, optional thin aliases; no bundle API or `registry/index.json` change unless follow-up tasks add validators that touch tooling paths.
- **OpenSpec**: `openspec/config.yaml`, `openspec/CHANGE_ORDER.md`, and workflow notes for agents.
- **Tests/tooling**: New or extended tests/validators for governance markdown frontmatter, required always-load files, deterministic index semantics, canonical `applies_when` signals, and hierarchy-cache hardening behavior (under `tests/` or existing doc-validation harness as appropriate).
- **Cross-repo**: Behavioral parity with specfact-cli governance-03; modules remains authoritative for bundle/registry release policy references inside rule text.

## Tracking

- GitHub Issue: [#181](https://github.com/nold-ai/specfact-cli-modules/issues/181)
- Parent Feature: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163)
- Paired core (specfact-cli): [specfact-cli#494](https://github.com/nold-ai/specfact-cli/issues/494) — deterministic agent governance loading
- Related modules baseline: [specfact-cli-modules#178](https://github.com/nold-ai/specfact-cli-modules/issues/178) — hierarchy cache (`governance-03-github-hierarchy-cache`)
