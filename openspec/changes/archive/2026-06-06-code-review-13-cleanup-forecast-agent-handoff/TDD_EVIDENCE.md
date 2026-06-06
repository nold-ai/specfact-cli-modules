# TDD Evidence: code-review-13-cleanup-forecast-agent-handoff

## Failing-before evidence

Command:

```bash
hatch run pytest tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/review/test_commands.py -q
```

Result before implementation:

- Exit code: 2
- Collection failed because `AiBloatIndex` and `_preserve_reasons_for_finding` did not exist yet.

## Passing evidence

Targeted implementation command:

```bash
hatch run pytest tests/unit/specfact_code_review/run/test_cleanup_evidence.py tests/unit/specfact_code_review/run/test_forecast.py tests/unit/specfact_code_review/run/test_findings.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/review/test_commands.py -q
```

Result after implementation:

- Exit code: 0
- 137 passed

Docs and packaged-resource parity command:

```bash
hatch run pytest tests/unit/docs/test_code_review_docs_parity.py tests/unit/specfact_code_review/rules/test_updater.py tests/unit/test_guided_simplify_resources.py -q
```

Result:

- Exit code: 0
- 22 passed

Required final gates:

- `hatch run format` — exit code 0
- `hatch run type-check` — exit code 0
- `hatch run lint` — exit code 0
- `hatch run yaml-lint` — exit code 0
- `hatch run check-bundle-imports` — exit code 0
- `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump` — exit code 0
- `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope changed` — exit code 0
- `openspec validate code-review-13-cleanup-forecast-agent-handoff --strict` — exit code 0

Full suite wrappers:

- `hatch run contract-test -- tests/cli-contracts/specfact-code-review-run.scenarios.yaml` — exit code 0, 785 passed, 2 warnings
- `hatch run smart-test` — exit code 0, 785 passed, 2 warnings
- `hatch run test -- -q` — exit code 0, 785 passed, 2 warnings
