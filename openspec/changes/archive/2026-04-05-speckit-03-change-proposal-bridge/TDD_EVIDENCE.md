# TDD Evidence: speckit-03-change-proposal-bridge

## Verification Evidence

### 0. Failing evidence

N/A for a captured terminal snapshot on this branch. The failing pre-implementation state was the absence of the new surface entirely:

- `SpecKitConverter.convert_to_change_proposal(...)` did not exist.
- `SpecKitConverter.convert_to_speckit_feature(...)` did not exist.
- `specfact sync bridge --adapter speckit --mode change-proposal` did not exist.
- `SpecKitBacklogSync` did not exist.

The tests added in this change encode that missing behavior and now pass against the implementation below.

### 1. Speckit conversion and sync tests

Command run on 2026-03-28:

```bash
python3 -m pytest tests/unit/importers/test_speckit_converter.py tests/unit/sync_runtime/test_speckit_backlog_sync.py tests/unit/sync_runtime/test_bridge_sync_speckit_backlog.py tests/unit/sync/test_change_proposal_mode.py -q
```

Result:

```text
collected 13 items
13 passed in 2.19s
```

### 2. Documentation validation

Commands run on 2026-03-28:

```bash
python3 scripts/check-docs-commands.py
python3 -m pytest tests/unit/docs/test_docs_review.py -q
```

Result:

```text
Docs command validation passed with no findings.
19 passed
```

### 3. Focused code review

Command run on 2026-03-28:

```bash
specfact code review run packages/specfact-project/src/specfact_project/importers/speckit_change_proposal_bridge.py packages/specfact-project/src/specfact_project/sync_runtime/speckit_backlog_sync.py packages/specfact-project/src/specfact_project/sync_runtime/speckit_bridge_backlog.py packages/specfact-project/src/specfact_project/sync_runtime/speckit_change_proposal_sync.py tests/unit/importers/test_speckit_converter.py tests/unit/sync/test_change_proposal_mode.py tests/unit/sync_runtime/test_bridge_sync_speckit_backlog.py tests/unit/sync_runtime/test_speckit_backlog_sync.py --no-tests
```

Result:

```text
Review completed with no findings.
Verdict: PASS | CI exit: 0
```

### 4. Quality gates completed

Commands run on 2026-03-28:

```bash
hatch run format
hatch run type-check
hatch run lint
hatch run yaml-lint
```

Result:

```text
format: 2 errors fixed, 0 remaining
type-check: 0 errors, 0 warnings, 0 notes
lint: All checks passed, pylint 10.00/10
yaml-lint: Validated 6 manifests and registry/index.json
```

### 5. Signature gate status

Command run on 2026-03-28:

```bash
hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump
```

Current result before manual signing:

```text
FAIL packages/specfact-project/module-package.yaml: checksum mismatch
```

This is expected after the `specfact-project` bundle version bump and payload changes. The user will sign modules manually after implementation.

### 6. Cross-repo integration gate note

The local canonical sibling checkout at `/home/dom/git/nold-ai/specfact-cli` currently contains merge-conflict markers in `src/specfact_cli/__init__.py`, so long-running gates that import the core CLI must be run against a clean `specfact-cli` worktree instead. Local reruns used:

```bash
PYTHONPATH=/home/dom/git/nold-ai/specfact-cli-worktrees/feature/speckit-02-v04-adapter-alignment/src ...
```

### 7. Long-running test gates

Commands run on 2026-03-28 against the clean core worktree:

```bash
PYTHONPATH=/home/dom/git/nold-ai/specfact-cli-worktrees/feature/speckit-02-v04-adapter-alignment/src hatch run contract-test
PYTHONPATH=/home/dom/git/nold-ai/specfact-cli-worktrees/feature/speckit-02-v04-adapter-alignment/src hatch run smart-test
PYTHONPATH=/home/dom/git/nold-ai/specfact-cli-worktrees/feature/speckit-02-v04-adapter-alignment/src hatch run test
```

Result:

```text
contract-test: 446 passed in 133.35s
smart-test: 446 passed in 128.77s
test: 446 passed in 41.51s
```
