# Change Validation: governance-04-deterministic-agent-governance-loading

- **Validated on (local):** 2026-04-12
- **Strict command:** `openspec validate governance-04-deterministic-agent-governance-loading --strict`
- **Result:** **PENDING / BLOCKED** — `openspec validate … --strict` passed, but the mandatory full-repo SpecFact code review gate is still **FAIL** (`.specfact/code-review.json` reports **934** findings). Do not mark this change fully validated until `hatch run specfact code review run --json --out .specfact/code-review.json --scope full` exits **PASS** or an explicit, approved exception is recorded.

## Scope summary

- **New capability:** `agent-governance-loading`
- **Modified capability:** `github-hierarchy-cache` (session-bootstrap cache refresh scenario, repo-aware state reuse, and cache-refresh CLI failure signaling; cache-first guidance also references `openspec/config.yaml`)

## Commands run

- `openspec validate governance-04-deterministic-agent-governance-loading --strict` → PASS
- `git worktree repair <WORKTREE_ROOT>` → PASS
- `hatch run smart-test-status` → PASS
- `hatch run contract-test-status` → PASS
- `python3 -m pytest tests/unit/docs/test_agent_rules_governance.py tests/unit/scripts/test_validate_agent_rule_applies_when.py tests/unit/scripts/test_sync_github_hierarchy_cache.py -q` → PASS
- `hatch run format` → PASS
- `hatch run type-check` → PASS
- `hatch run lint` → PASS
- `hatch run yaml-lint` → PASS
- `hatch run validate-agent-rule-signals` → PASS
- `hatch run test tests/unit/docs/test_agent_rules_governance.py tests/unit/scripts/test_validate_agent_rule_applies_when.py tests/unit/scripts/test_sync_github_hierarchy_cache.py -q` → PASS (repo helper executed the full `tests/` tree; 531 passed)
- `hatch run contract-test` → PASS (531 passed)
- `hatch run smart-test` → PASS (531 passed)
- `PATH=<WORKTREE_ROOT>/.venv/bin:$PATH hatch run specfact code review run --json --out .specfact/code-review.changed.json --scope changed` → PASS (report generated, `0` findings)
- `hatch run specfact code review run --json --out .specfact/code-review.json --scope full` → FAIL (report generated)

## Notes

- The worktree path is correctly registered in Git under `<WORKTREE_ROOT>` (local clone path; not committed as a fixed absolute path).
- `.specfact/code-review.json` is now generated successfully, but the full review exits `FAIL` with 934 findings from the existing repo-wide surface. The command is no longer blocked by missing module setup.
- `.specfact/code-review.changed.json` now passes cleanly for the branch-local surface after repairing moved-worktree Semgrep launcher shebangs in the ignored `.venv/bin/semgrep` and `.venv/bin/pysemgrep` entrypoints.
