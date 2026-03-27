---
layout: default
title: Code review run
nav_order: 3
permalink: /bundles/code-review/run/
redirect_from:
  - /guides/code-review-run/
---

# Code review run

`specfact code review run` executes the governed review pipeline for a set of files or for an auto-detected repo scope.

## Command

- `specfact code review run [FILES...]`

## Key options

| Option | Purpose |
|--------|---------|
| `--scope changed|full` | Review changed files or the full repository when no positional files are provided |
| `--path <prefix>` | Narrow auto-discovered review files to one or more repo-relative prefixes |
| `--include-tests`, `--exclude-tests` | Control whether changed test files participate in auto-scope review |
| `--include-noise`, `--suppress-noise` | Keep or suppress known low-signal findings |
| `--json` | Emit a `ReviewReport` JSON file |
| `--out <path>` | Override the default JSON output path |
| `--score-only` | Print just the reward delta integer |
| `--no-tests` | Skip the TDD gate |
| `--fix` | Apply Ruff autofixes, then rerun the review |
| `--interactive` | Prompt for scope decisions before execution |

## Examples

```bash
specfact code review run --scope changed
specfact code review run --scope full --path packages/specfact-code-review
specfact code review run --json --out /tmp/review-report.json packages/specfact-code-review/src/specfact_code_review/run/commands.py
specfact code review run --score-only packages/specfact-code-review/src/specfact_code_review/run/commands.py
specfact code review run --fix packages/specfact-code-review/src/specfact_code_review/run/commands.py
```

## Bundle-owned resources

The review pipeline uses rules, skills, and policy payloads shipped with the installed Code Review bundle. Those assets are bundle-owned and should be refreshed through supported bundle and IDE setup flows rather than legacy core-owned paths.

## Related

- [Code review ledger](ledger/)
- [Code review rules](rules/)
- [Code review module guide](../../modules/code-review/)
