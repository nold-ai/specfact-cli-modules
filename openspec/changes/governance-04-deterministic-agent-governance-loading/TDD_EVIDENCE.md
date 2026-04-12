# TDD Evidence: governance-04-deterministic-agent-governance-loading

## Notes

- This implementation session started from already-finalized spec artifacts synced from `origin/dev`.
- Passing-after verification is recorded below.
- Failing-first evidence was not captured before the pushed artifact updates landed in the worktree; task `2.3` remains open until that gap is explicitly resolved or waived.

## Passing-after commands

- 2026-04-12: `openspec validate governance-04-deterministic-agent-governance-loading --strict` → PASS
- 2026-04-12: `git worktree repair /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/governance-04-deterministic-agent-governance-loading` → PASS
- 2026-04-12: `hatch run smart-test-status` → PASS
- 2026-04-12: `hatch run contract-test-status` → PASS
- 2026-04-12: `python3 -m pytest tests/unit/docs/test_agent_rules_governance.py tests/unit/scripts/test_validate_agent_rule_applies_when.py tests/unit/scripts/test_sync_github_hierarchy_cache.py -q` → PASS
- 2026-04-12: `SPECFACT_CLI_REPO=/home/dom/git/nold-ai/specfact-cli hatch run dev-deps` → PASS
- 2026-04-12: `hatch run format` → PASS
- 2026-04-12: `hatch run type-check` → PASS
- 2026-04-12: `hatch run lint` → PASS
- 2026-04-12: `hatch run yaml-lint` → PASS
- 2026-04-12: `hatch run validate-agent-rule-signals` → PASS
- 2026-04-12: `hatch run test tests/unit/docs/test_agent_rules_governance.py tests/unit/scripts/test_validate_agent_rule_applies_when.py tests/unit/scripts/test_sync_github_hierarchy_cache.py -q` → PASS (helper executed the full `tests/` tree; 531 passed)
- 2026-04-12: `hatch run contract-test` → PASS (531 passed)
- 2026-04-12: `hatch run smart-test` → PASS (531 passed)
- 2026-04-12: `PATH=/home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/governance-04-deterministic-agent-governance-loading/.venv/bin:$PATH hatch run specfact code review run --json --out .specfact/code-review.changed.json --scope changed` → PASS (`overall_verdict=PASS`, `0` findings)

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
  - Because the worktree moved from `/home/dom/git/...` to `/home/dom/git/nold-ai/...`, the ignored `.venv/bin/semgrep` and `.venv/bin/pysemgrep` entrypoints had stale absolute shebangs. Those local launchers were repaired in-place so changed-scope code review could run successfully from the corrected worktree path.
