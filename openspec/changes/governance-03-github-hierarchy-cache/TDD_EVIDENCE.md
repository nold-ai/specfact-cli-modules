# TDD Evidence

## Failing-before implementation

- Timestamp: `2026-04-09T21:03:37+02:00`
- Command: `python3 -m pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py -q`
- Result: FAIL
- Summary: All three tests failed with `FileNotFoundError` because `scripts/sync_github_hierarchy_cache.py` did not exist yet.

## Failing-before path relocation refinement

- Timestamp: `2026-04-09T21:17:04+02:00`
- Command: `python3 -m pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py -q`
- Result: FAIL
- Summary: The new default-path test failed because the script still targeted `openspec/GITHUB_HIERARCHY_CACHE.md` instead of ignored `.specfact/backlog/` storage.

## Passing-after implementation

- Timestamp: `2026-04-09T21:17:35+02:00`
- Command: `python3 -m pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py -q`
- Result: PASS
- Summary: All five script tests passed after moving the cache into ignored `.specfact/backlog/` storage and keeping the no-op fingerprint path intact.

## Additional verification

- `python3 -m py_compile scripts/sync_github_hierarchy_cache.py` → PASS
- `python3 scripts/sync_github_hierarchy_cache.py --force` → generated `.specfact/backlog/github_hierarchy_cache.md`
- Second `python3 scripts/sync_github_hierarchy_cache.py` run → `GitHub hierarchy cache unchanged (13 issues).`

## Final scoped quality gates

Full gate order (per `AGENTS.md` / `CLAUDE.md`). Run from repo root before merge; record PASS/FAIL after each step:

1. `hatch run format` → PASS
2. `hatch run type-check` → PASS
3. `hatch run lint` → PASS
4. `hatch run yaml-lint` → PASS
5. `hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump` → PASS
6. `hatch run contract-test` → PASS
7. `hatch run smart-test` → PASS
8. `hatch run test` → PASS
9. `hatch run specfact code review run --json --out .specfact/code-review.json` → PASS (`overall_verdict` PASS, `ci_exit_code` 0)

**Scoped exception:** None for this change; the list above is the required sequence. If CI or policy later narrows scope for a hotfix, update this block with an explicit rationale, approver, and approval id/date instead of omitting gates.

### `.specfact/code-review.json` (this change)

- Last refresh: `2026-04-09T21:05:38Z` (UTC), command: `hatch run specfact code review run --json --out .specfact/code-review.json --scope changed`
- Outcome: PASS. Any low-severity DRY hints on icontract precondition helpers are documented under **Code review note** in `proposal.md` (accepted; do not merge predicates in ways that break icontract binding).
