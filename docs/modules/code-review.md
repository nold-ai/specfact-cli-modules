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
