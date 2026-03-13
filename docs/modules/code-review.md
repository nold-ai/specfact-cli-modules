# specfact-code-review module notes

## Tool runners

The `specfact-code-review` bundle now includes internal runners that translate tool
output into governed `ReviewFinding` records.

### Ruff runner

`specfact_code_review.tools.ruff_runner.run_ruff(files)` executes:

```bash
ruff check --output-format json <files...>
```

Rule prefixes are mapped as follows:

| Ruff rule prefix | ReviewFinding category |
| --- | --- |
| `S*` | `security` |
| `C9*` | `clean_code` |
| `E*` | `style` |
| `F*` | `style` |
| `I*` | `style` |
| `W*` | `style` |

Additional behavior:

- only the provided file list is considered
- unsupported Ruff rule families are skipped instead of being mislabeled
- a non-empty Ruff `fix` payload sets `fixable=True`
- malformed output or a missing Ruff executable yields a single `tool_error` finding

### Radon runner

`specfact_code_review.tools.radon_runner.run_radon(files)` executes:

```bash
radon cc -j <files...>
```

Cyclomatic complexity thresholds:

| Complexity | Severity | Category |
| --- | --- | --- |
| `<= 12` | no finding | n/a |
| `13..15` | `warning` | `clean_code` |
| `> 15` | `error` | `clean_code` |

Additional behavior:

- the default Hatch environment installs `radon`, so the runner is usable in standard repo workflows
- only the provided file list is considered
- malformed output or a missing Radon executable yields a single `tool_error` finding

### basedpyright runner

`specfact_code_review.tools.basedpyright_runner.run_basedpyright(files)` executes:

```bash
basedpyright --outputjson --project . <files...>
```

Diagnostic mapping:

| basedpyright severity | ReviewFinding severity | ReviewFinding category |
| --- | --- | --- |
| `error` | `error` | `type_safety` |
| `warning` | `warning` | `type_safety` |
| `information` | `info` | `type_safety` |

Additional behavior:

- basedpyright runs with project context and then filters findings back to the provided changed-file list
- the runner preserves per-diagnostic line numbers and falls back to rule `basedpyright` when the payload omits a specific rule id
- malformed output or a missing basedpyright executable yields a single `tool_error` finding

### pylint runner

`specfact_code_review.tools.pylint_runner.run_pylint(files)` executes:

```bash
pylint --output-format json <files...>
```

Governance-oriented message mapping:

| Pylint message id | ReviewFinding category |
| --- | --- |
| `W0702` | `architecture` |
| `W0703` | `architecture` |
| `T201` | `architecture` |
| `W1505` | `architecture` |
| other ids | `style` |

Additional behavior:

- only the provided changed-file list is reported back, even when pylint emits findings for other files
- severity is derived from the message id prefix (`E*`/`F*` -> `error`, `I*` -> `info`, otherwise `warning`)
- malformed output or a missing pylint executable yields a single `tool_error` finding

### Contract runner

`specfact_code_review.tools.contract_runner.run_contract_check(files)` combines two
contract-oriented checks:

1. an AST scan for public functions missing `@require` / `@ensure`
2. a CrossHair fast pass

AST scan behavior:

- only public module-level and class-level functions are checked
- functions prefixed with `_` are treated as private and skipped
- missing icontract decorators become `contracts` findings with rule
  `MISSING_ICONTRACT`
- unreadable or invalid Python files degrade to a single `tool_error` finding instead
  of raising

CrossHair behavior:

```bash
crosshair check --per_path_timeout 2 <files...>
```

- CrossHair counterexamples map to `contracts` warnings with tool `crosshair`
- timeouts are skipped so the AST scan can still complete
- missing CrossHair binaries degrade to a single `tool_error` finding

Operational note:

- the current development environment includes CrossHair, but installed-user
  environments still need that executable available for the fast pass to run

## Review orchestration

`specfact_code_review.run.runner.run_review(files, no_tests=False)` orchestrates the
bundle runners in this order:

1. Ruff
2. Radon
3. basedpyright
4. pylint
5. contract runner
6. TDD gate, unless `no_tests=True`

The merged findings are then scored into a governed `ReviewReport`.

### TDD gate

`specfact_code_review.run.runner.run_tdd_gate(files)` enforces a bundle-local
test-before-code rule for changed files under
`packages/specfact-code-review/src/specfact_code_review/...`.

For each changed source file, the runner expects a matching unit test under
`tests/unit/specfact_code_review/...` using the `test_<module>.py` naming pattern.

Current behavior:

- missing expected test file -> `TEST_FILE_MISSING`, `testing`, `error`
- targeted pytest failure -> `TEST_FAILURE`, `testing`, `error`
- coverage below 80% -> `TEST_COVERAGE_LOW`, `testing`, `warning`
- `no_tests=True` skips the TDD gate entirely
