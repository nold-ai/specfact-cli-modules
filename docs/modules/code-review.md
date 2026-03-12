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
