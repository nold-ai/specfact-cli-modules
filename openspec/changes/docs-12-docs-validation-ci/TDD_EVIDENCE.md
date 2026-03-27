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

### 0.1 Repo-wide failing command audit after matcher fix

Pre-cleanup audit run from `2026-03-28T00:03:00+01:00`:

```bash
python3 - <<'PY'
from pathlib import Path
import importlib.util
repo = Path('.').resolve()
path = repo / 'scripts' / 'check-docs-commands.py'
spec = importlib.util.spec_from_file_location('check_docs_commands', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
paths = sorted(p.resolve() for p in (repo / 'docs').rglob('*.md'))
valid = mod._build_valid_command_paths()
findings = mod._validate_command_examples(paths, valid)
for finding in findings[:300]:
    rel = finding.source.relative_to(repo)
    print(f"{rel}:{finding.line_number}: {finding.message}")
print(f"TOTAL_FINDINGS={len(findings)}")
PY
```

Failing excerpt:

```text
docs/getting-started/README.md:48: Unknown command example: specfact validate ...
docs/guides/agile-scrum-workflows.md:117: Unknown command example: specfact policy validate --repo . --format both
docs/integrations/devops-adapter-overview.md:23: Unknown command example: specfact policy validate --repo . --format both
docs/reference/architecture.md:14: Unknown command example: specfact architecture derive|validate|trace
TOTAL_FINDINGS=39
```

This exposed the remaining stale former command references outside the original bundle-only validation scope.

### 0.2 Docs review warning snapshot before cleanup

Pre-cleanup docs review run from `2026-03-28T00:19:32+01:00`:

```bash
python3 -m pytest tests/unit/docs/test_docs_review.py -q
```

Failing excerpt:

```text
UserWarning: Pre-existing docs files missing front matter (6):
docs/getting-started/tutorial-openspec-speckit.md
docs/module-publishing-guide.md
docs/reference/feature-keys.md
docs/reference/parameter-standard.md
docs/reference/specmatic.md
docs/reference/telemetry.md
UserWarning: Pre-existing broken authored docs links (56 total):
docs/adapters/azuredevops.md -> ../guides/devops-adapter-integration.md
...
======================== 19 passed, 2 warnings in 0.41s ========================
```

This captured the remaining published-doc warnings before the final stale-link and front-matter cleanup.

### 1. Validator passes after docs fixes

Passing run from `2026-03-27T23:19:08+01:00`:

```bash
python3 scripts/check-docs-commands.py
```

Passing excerpt:

```text
Docs command validation passed with no findings.
```

This verifies the scripted checks for implemented command examples, stale core-owned resource paths, and allowed `docs.specfact.io` cross-site URLs all pass after the initial docs fixes.

### 2. Script unit coverage

Passing run from `2026-03-27T23:18:24+01:00`:

```bash
python3 -m pytest tests/unit/test_check_docs_commands_script.py -q
```

Passing excerpt:

```text
.....                                                                    [100%]
6 passed in 0.31s
```

This covers command extraction, command matching, repo-wide docs target discovery, stale legacy resource detection, cross-site link validation, and docs workflow integration.

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

This earlier run confirmed the new validator and the existing authored-docs checks pass together before the warning cleanup was completed.

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

### 5.1 Repo-wide published docs command audit passes

Passing audit run from `2026-03-28T00:07:33+01:00`:

```bash
python3 - <<'PY'
from pathlib import Path
import importlib.util
repo = Path('.').resolve()
path = repo / 'scripts' / 'check-docs-commands.py'
spec = importlib.util.spec_from_file_location('check_docs_commands', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
paths = mod._iter_validation_docs_paths()
valid = mod._build_valid_command_paths()
findings = mod._validate_command_examples(paths, valid)
for finding in findings[:300]:
    rel = finding.source.relative_to(repo)
    print(f"{rel}:{finding.line_number}: {finding.message}")
print(f"TOTAL_FINDINGS={len(findings)}")
PY
```

Passing excerpt:

```text
TOTAL_FINDINGS=0
```

This verifies the widened validator catches and clears stale former command references across published module docs, not only bundle reference pages.

### 5.2 Docs review warnings eliminated

Passing run from `2026-03-28T00:19:32+01:00`:

```bash
python3 -m pytest tests/unit/docs/test_docs_review.py -q
```

Passing excerpt:

```text
tests/unit/docs/test_docs_review.py ...................                  [100%]
============================== 19 passed in 0.43s ==============================
```

This verifies the previously tolerated warnings are gone: published docs now have the missing front matter added and the stale internal links updated to current canonical modules-docs routes.

### 5.3 Combined docs validation suite

Passing run from `2026-03-28T00:19:32+01:00`:

```bash
python3 -m pytest tests/unit/docs/test_docs_review.py tests/unit/docs/test_missing_command_docs.py tests/unit/docs/test_bundle_overview_cli_examples.py tests/unit/test_check_docs_commands_script.py -q
```

Passing excerpt:

```text
..............................                                           [100%]
============================== 30 passed in 4.16s ==============================
```

This verifies the docs review gate, bundle command docs checks, overview smoke routing, and the command validator tests all pass together after the warning cleanup.

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
