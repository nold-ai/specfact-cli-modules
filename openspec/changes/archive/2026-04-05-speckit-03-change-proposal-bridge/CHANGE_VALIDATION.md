# Change Validation Report: speckit-03-change-proposal-bridge

**Validation Date**: 2026-03-28
**Change Proposal**: [proposal.md](./proposal.md)
**Validation Method**: Implemented-code verification, targeted tests, focused code review, docs audit

## Executive Summary

- Breaking Changes: 0 detected
- Dependent Files: 7 primary implementation files plus tests and docs
- Impact Level: Medium
- Validation Result: Partial pass pending manual module signing and completion of long-running gate reruns
- User Decision: User will sign modules manually

## Implementation Summary

The change is implemented as additive behavior:

- `SpecKitConverter` now exposes:
  - `convert_to_change_proposal(feature_path, change_name, output_dir)`
  - `convert_to_speckit_feature(change_dir, output_dir)`
- New helper module `speckit_change_proposal_bridge.py` isolates the change-proposal mapping logic.
- New helper module `speckit_backlog_sync.py` detects extension-created issue references in Spec-Kit task files.
- New helper module `speckit_bridge_backlog.py` imports those references into backlog sync source tracking.
- `specfact sync bridge --adapter speckit --mode change-proposal` supports:
  - `--feature <name>`
  - `--all`
  - feature tracking via proposal markers
  - fallback profile detection to `solo`
- Docs were updated to align with current Spec-Kit flow and current bridge command syntax.

## Dependency Review

### Cross-repo dependencies

| Dependency | Status | Impact |
|---|---|---|
| `specfact-cli` Speckit v0.4.x support | Present in clean worktree | Needed to validate current command vocabulary and integration assumptions |
| `profile-01` config layering | Not present in this repo | Change falls back to `solo` and only emits non-solo warnings when a profile marker exists |

### Local dependency assessment

- No existing module commands were removed or renamed.
- Existing `sync bridge` modes remain unchanged.
- Backlog duplicate prevention is additive and only activates when Spec-Kit mappings are detected.

## Speckit Flow Validation

Official Speckit docs were rechecked against the current site copy during this change. The current canonical flow is:

`/constitution -> /specify -> /clarify -> /plan -> /tasks -> /analyze -> /implement`

Validation outcome:

- Older local docs that implied `/speckit.*` commands were current were stale and were corrected.
- Older local docs that skipped `/clarify` and `/analyze` in the primary path were stale and were corrected.
- Our current docs now reflect the current slash-command names and the current flow order.
- Nuance: `/clarify` can still be intentionally skipped, but the default documented path should include it before `/plan`.

## Quality Validation

Completed:

- `python3 -m pytest tests/unit/importers/test_speckit_converter.py tests/unit/sync_runtime/test_speckit_backlog_sync.py tests/unit/sync_runtime/test_bridge_sync_speckit_backlog.py tests/unit/sync/test_change_proposal_mode.py -q`
- `python3 scripts/check-docs-commands.py`
- `python3 -m pytest tests/unit/docs/test_docs_review.py -q`
- `specfact code review run ... --no-tests` on extracted Speckit helper scope with 0 findings
- `hatch run format`
- `hatch run type-check`
- `hatch run lint`
- `hatch run yaml-lint`
- `PYTHONPATH=/home/dom/git/nold-ai/specfact-cli-worktrees/feature/speckit-02-v04-adapter-alignment/src hatch run contract-test`
- `PYTHONPATH=/home/dom/git/nold-ai/specfact-cli-worktrees/feature/speckit-02-v04-adapter-alignment/src hatch run smart-test`
- `PYTHONPATH=/home/dom/git/nold-ai/specfact-cli-worktrees/feature/speckit-02-v04-adapter-alignment/src hatch run test`

Pending / blocked:

- `hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump`
  - currently fails on `packages/specfact-project/module-package.yaml: checksum mismatch`
  - expected until the user performs manual module signing
- the long-running gates had to be executed against a clean `specfact-cli` worktree because the canonical sibling checkout currently has merge-conflict markers in `specfact_cli/__init__.py`

## Code Review Validation

Broad file-level `specfact code review run` on the touched legacy monoliths surfaces inherited complexity debt from:

- `packages/specfact-project/src/specfact_project/importers/speckit_converter.py`
- `packages/specfact-project/src/specfact_project/sync/commands.py`
- `packages/specfact-project/src/specfact_project/sync_runtime/bridge_sync.py`

To keep the change reviewable without rewriting unrelated legacy modules, the new Speckit logic was extracted into helper modules and reviewed on that isolated delta. The focused review scope passed with 0 findings.

## OpenSpec Status

- `openspec validate speckit-03-change-proposal-bridge --strict` passed during implementation.
- `tasks.md` now reflects implemented vs pending work accurately.
- `TDD_EVIDENCE.md` was added and records the relevant verification evidence.
