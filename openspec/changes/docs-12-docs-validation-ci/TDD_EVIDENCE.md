# TDD Evidence

## Verification Evidence

### 0. Failing evidence

Pre-fix validation run from `2026-03-27T23:12:35+01:00`:

```bash
python3 scripts/check-docs-commands.py
```

Failing excerpt:

```text
docs/bundles/backlog/policy-engine.md:28: [command] Unknown command example: specfact policy init --repo . --template scrum
docs/bundles/backlog/policy-engine.md:41: [command] Unknown command example: specfact policy init --repo .
docs/bundles/backlog/policy-engine.md:51: [command] Unknown command example: specfact policy validate --repo . --format both
docs/bundles/backlog/policy-engine.md:91: [command] Unknown command example: specfact policy suggest --repo .
docs/reference/commands.md:13: [command] Unknown command example: specfact --help
docs/bundles/backlog/refinement.md:788: [legacy-resource] Legacy core-owned resource reference: src/specfact_cli/templates
```

This captured the initial failing state before the validator and docs fixes were completed.

### 1. Validator passes after docs fixes

Passing run from `2026-03-27T23:19:08+01:00`:

```bash
python3 scripts/check-docs-commands.py
```

Passing excerpt:

```text
Docs command validation passed with no findings.
```

This verifies the scripted checks for implemented command examples, stale core-owned resource paths, and allowed `docs.specfact.io` cross-site URLs all pass after the docs fixes.

### 2. Script unit coverage

Passing run from `2026-03-27T23:18:24+01:00`:

```bash
python3 -m pytest tests/unit/test_check_docs_commands_script.py -q
```

Passing excerpt:

```text
.....                                                                    [100%]
5 passed in 0.08s
```

This covers command extraction, command matching, stale legacy resource detection, cross-site link validation, and docs workflow integration.

### 3. Docs review plus validator regression coverage

Passing run from `2026-03-27T23:20:13+01:00`:

```bash
python3 -m pytest tests/unit/docs/test_docs_review.py tests/unit/test_check_docs_commands_script.py -q
```

Passing excerpt:

```text
.....................                                                    [100%]
21 passed, 2 warnings in 0.21s
```

The warnings are pre-existing docs-review warnings unrelated to this change. The run confirms the new validator and the existing authored-docs checks pass together.

### 4. Review gate stays clean

Passing run from `2026-03-27T23:21:05+01:00`:

```bash
specfact code review run scripts/check-docs-commands.py tests/unit/test_check_docs_commands_script.py --no-tests
```

Passing excerpt:

```text
Review completed with no findings.
```

This verifies the new script and its tests satisfy the required code-review gate.

### 5. CI docs-review workflow wiring

The docs review workflow now includes the validator script and its tests:

```text
.github/workflows/docs-review.yml
- triggers on changes to scripts/check-docs-commands.py and tests/unit/test_check_docs_commands_script.py
- runs: python scripts/check-docs-commands.py
```

This, together with the passing local validator and docs test runs above, provides the end-to-end evidence for the workflow path required by task 5.3.

### 6. Full repository quality gates

Passing quality gate sequence completed on `2026-03-27`:

```bash
hatch run format
hatch run type-check
hatch run lint
hatch run yaml-lint
hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump
hatch run contract-test
hatch run smart-test
hatch run test
```

Summary excerpts:

```text
type-check: 0 errors, 0 warnings, 0 notes
contract-test: 427 passed, 2 warnings
smart-test: 427 passed, 2 warnings
test: 427 passed, 2 warnings in 34.16s
```

This confirms the change passes the repository quality gates in the required order.
