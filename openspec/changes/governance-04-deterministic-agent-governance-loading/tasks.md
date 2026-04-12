# Tasks: governance-04-deterministic-agent-governance-loading

## 1. Branch, tracking, and worktree setup

- [x] 1.1 Confirm GitHub issue exists for this change, is linked under **Parent Feature [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163)**, and **proposal.md → Tracking** lists the issue URL and paired core [specfact-cli#494](https://github.com/nold-ai/specfact-cli/issues/494). Update **openspec/CHANGE_ORDER.md** (Validation and governance section) with a new row: `governance | 04 | governance-04-deterministic-agent-governance-loading | <modules-issue#> | Parent #163; paired core #494; baseline #178`.
- [x] 1.2 Before implementation edits, create a dedicated worktree from `origin/dev` (not the primary `dev` checkout): `git fetch origin` then `git worktree add ../specfact-cli-modules-worktrees/feature/governance-04-deterministic-agent-governance-loading -b feature/governance-04-deterministic-agent-governance-loading origin/dev`. Treat that path as relative to the repo parent (`/home/dom/git/nold-ai/` in this environment) when rendering absolute paths.
- [x] 1.3 In the worktree: `hatch env create` and `hatch run dev-deps` so `specfact` CLI is available for code-review dogfood tasks.
- [x] 1.4 Pre-flight from worktree: `hatch run smart-test-status` and `hatch run contract-test-status` (or full quick sanity per AGENTS.md if those targets differ).
- [x] 1.5 Run `openspec validate governance-04-deterministic-agent-governance-loading --strict` and capture output in `CHANGE_VALIDATION.md`; fix artifact issues until green.
- [ ] 1.6 After PR merges: `git worktree remove`, `git branch -d`, `git worktree prune` for the feature branch; remove worktree-local `.venv` if unused.

## 2. Spec-first and test-first preparation

- [x] 2.1 Finalize spec deltas for `agent-governance-loading` and `github-hierarchy-cache`; re-run `openspec validate governance-04-deterministic-agent-governance-loading --strict` after edits.
- [x] 2.2 Add or extend tests (or doc-validation hooks) covering: required YAML frontmatter on `docs/agent-rules/*.md`, presence of always-load files referenced from `INDEX.md`, deterministic ordering/precedence statements where encoded in tests, bootstrap text that requires cache refresh when missing/stale, canonical `applies_when` signal validation, and cache-script repo/error hardening behavior (align with paired specfact-cli validators where practical).
- [ ] 2.3 Record failing-first evidence in `TDD_EVIDENCE.md` before editing governance markdown or shrinking `AGENTS.md`.

## 3. Governance implementation

- [x] 3.1 Replace the long-form `AGENTS.md` body with a compact bootstrap contract that matches **specfact-cli** semantics but preserves modules-specific quality-gate ordering (format, type-check, lint, yaml-lint, **verify-modules-signature**, contract-test, smart-test, test) by reference to `docs/agent-rules/` rather than inline duplication where possible.
- [x] 3.2 Add `docs/agent-rules/INDEX.md`, `docs/agent-rules/05-non-negotiable-checklist.md`, and domain rule files (`10`–`80` series per design) adapted from **specfact-cli** for modules paths, worktree location `../specfact-cli-modules-worktrees/`, hierarchy script `python scripts/sync_github_hierarchy_cache.py`, bundle/registry policy, and SpecFact code-review JSON dogfood rules.
- [x] 3.3 Port the validator/test surfaces that enforce the rule system in **specfact-cli**: frontmatter-schema enforcement for `docs/agent-rules/*.md`, canonical `applies_when` validation, and governance-doc existence/reference tests adapted for the modules repo.
- [x] 3.4 Update thin alias surfaces to match the **specfact-cli** pattern: keep `CLAUDE.md` compact, add/update `.cursorrules` as a compact Cursor alias, add/update `.github/copilot-instructions.md` as a compact Copilot alias, and update docs navigation/frontmatter references plus **`openspec/config.yaml`** so long policy prose references canonical `docs/agent-rules/` where appropriate without duplicating the full handbook.
- [x] 3.5 Ensure session-bootstrap and `github-hierarchy-cache` guidance explicitly requires refreshing `.specfact/backlog/github_hierarchy_cache.md` when missing or stale before Epic/Feature parenting or blocker work.
- [x] 3.6 Implement or extend governance logic and docs so public-work readiness checks cover parent resolution, labels, project assignment, blockers / blocked-by relationships, and `in progress` issue-state clarification, matching the improved **specfact-cli** flow with modules-specific wording.
- [x] 3.7 Bring `scripts/sync_github_hierarchy_cache.py` and its tests up to current parity for deterministic bootstrap dependencies: repo-aware state matching, clear CLI error surfacing, and any accompanying spec wording or assertions.

## 4. Validation and documentation

- [x] 4.1 Run quality gates from the worktree until green: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run contract-test`, `hatch run smart-test`, `hatch run test` (add signature verify if any `module-package.yaml` / registry payload changes).
- [ ] 4.2 **SpecFact code review JSON**: ensure `.specfact/code-review.json` exists and is fresh per `openspec/config.yaml` rules; remediate all findings or document a rare justified exception in the proposal; record commands and timestamp in `TDD_EVIDENCE.md`.
- [x] 4.3 If contributor-facing docs under `docs/` must mention the new layout (e.g. onboarding, nav, frontmatter schema), update them without breaking Jekyll front matter or `documentation-url-contract.md` permalinks.
- [x] 4.4 Re-run `openspec validate governance-04-deterministic-agent-governance-loading --strict` and update `CHANGE_VALIDATION.md`.

## 5. Delivery

- [x] 5.1 Refresh `TDD_EVIDENCE.md` with passing-after commands and timestamps.
- [ ] 5.2 Open a PR from `feature/governance-04-deterministic-agent-governance-loading` to `dev` with summary linking modules issue, #163, #494, and #178.
- [ ] 5.3 After merge, run `openspec archive governance-04-deterministic-agent-governance-loading` from repo root (no manual folder moves) and confirm **openspec/CHANGE_ORDER.md** reflects archived status.
