# TDD Evidence: governance-04-deterministic-agent-governance-loading

## Notes

- This implementation session started from already-finalized spec artifacts synced from `origin/dev`.
- Passing-after verification is recorded below under **Passing-after commands**.

## Task 2.3 — failing-first evidence (waived)

**Requirement:** Record failing-first evidence before editing governance markdown or shrinking `AGENTS.md`.

**Resolution (waived — 2026-04-12):** A standalone timestamped log showing failing tests *before* any `docs/agent-rules/` files or compact `AGENTS.md` existed was not retained; development on this branch interleaved spec artifacts, tests from task **2.2**, and governance implementation (**3.x**) in close sequence.

**Rationale / provenance:** Behavior is enforced after the fact by automated checks, so the governance surface cannot regress silently:

| Check | Command / location |
|--------|---------------------|
| Required frontmatter keys on rule docs | `pytest tests/unit/docs/test_agent_rules_governance.py::test_agent_rule_docs_have_required_frontmatter_keys` |
| INDEX bootstrap metadata | `pytest tests/unit/docs/test_agent_rules_governance.py::test_agent_rules_index_has_deterministic_bootstrap_metadata` |
| Malformed frontmatter and `applies_when` signals | `pytest tests/unit/scripts/test_validate_agent_rule_applies_when.py` and `hatch run validate-agent-rule-signals` |

**Author:** Documented in-repo for audit trail per CodeRabbit / review request; strict chronological failing-first capture is waived for this change set.

## Passing-after commands

- 2026-04-12: `openspec validate governance-04-deterministic-agent-governance-loading --strict` → PASS
- 2026-04-12: `git worktree repair <WORKTREE_ROOT>` → PASS
- 2026-04-12: `hatch run smart-test-status` → PASS
- 2026-04-12: `hatch run contract-test-status` → PASS
- 2026-04-12: `python3 -m pytest tests/unit/docs/test_agent_rules_governance.py tests/unit/scripts/test_validate_agent_rule_applies_when.py tests/unit/scripts/test_sync_github_hierarchy_cache.py -q` → PASS
- 2026-04-12: `SPECFACT_CLI_REPO=<path-to-specfact-cli-checkout> hatch run dev-deps` → PASS
- 2026-04-12: `hatch run format` → PASS
- 2026-04-12: `hatch run type-check` → PASS
- 2026-04-12: `hatch run lint` → PASS
- 2026-04-12: `hatch run yaml-lint` → PASS
- 2026-04-12: `hatch run validate-agent-rule-signals` → PASS
- 2026-04-12: `hatch run test tests/unit/docs/test_agent_rules_governance.py tests/unit/scripts/test_validate_agent_rule_applies_when.py tests/unit/scripts/test_sync_github_hierarchy_cache.py -q` → PASS (helper executed the full `tests/` tree; 531 passed)
- 2026-04-12: `hatch run contract-test` → PASS (531 passed)
- 2026-04-12: `hatch run smart-test` → PASS (531 passed)
- 2026-04-12: `PATH=<WORKTREE_ROOT>/.venv/bin:$PATH hatch run specfact code review run --json --out .specfact/code-review.changed.json --scope changed` → PASS (`overall_verdict=PASS`, `0` findings)

## Remaining blocker

- 2026-04-12: `hatch run specfact code review run --json --out .specfact/code-review.json --scope full` → FAIL
- Current result: review artifact written at `.specfact/code-review.json`, verdict `FAIL`, `934` findings.
- The dominant findings are pre-existing clean-code complexity failures in legacy bundle code, for example `packages/specfact-backlog/src/specfact_backlog/backlog/commands.py`.
- The branch-local changed-files surface is now clean; the remaining blocker is only the full-repo quality surface required by task `4.2`.
- Setup steps completed before the review ran successfully:
  - `hatch run specfact module init --scope project` → seeded project-scope modules
  - `hatch run specfact module init --scope user` → seeded user-scope modules
  - `hatch run specfact module list --show-origin` → confirmed runtime bundle availability
  - `hatch run specfact module install nold-ai/specfact-codebase nold-ai/specfact-code-review --scope project --source bundled --repo . --reinstall` → bundled module artifacts not found for those ids
- Local worktree note:
  - After relocating the worktree directory, the ignored `.venv/bin/semgrep` and `.venv/bin/pysemgrep` entrypoints had stale absolute shebangs. Those local launchers were repaired in-place so changed-scope code review could run successfully from the corrected worktree path.
