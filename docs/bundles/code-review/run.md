---
layout: default
title: Code review run
nav_order: 3
permalink: /bundles/code-review/run/
redirect_from:
  - /guides/code-review-run/
keywords: [code-review, run, execution, analysis, review]
audience: [solo, team, enterprise]
expertise_level: [intermediate, advanced]
---

# Code review run

`specfact code review run` executes the governed review pipeline for a set of files or for an auto-detected repo scope.

The command prints **progress** to the terminal (spinner/status while the pipeline prepares and runs). With **`--json`**, it writes a machine-readable **`ReviewReport`** JSON file (defaulting to **`review-report.json`** in the working directory when **`--out`** is omitted).

## Command

- `specfact code review run [FILES...]`

## Key options

| Option | Purpose |
|--------|---------|
| `--scope changed\|full` | Review changed files or the full repository when no positional files are provided |
| `--path <prefix>` | Narrow auto-discovered review files to one or more repo-relative prefixes |
| `--include-tests`, `--exclude-tests` | Control whether changed test files participate in auto-scope review |
| `--focus <facet>` | Limit auto-discovered scope to **`source`**, **`tests`**, and/or **`docs`** (repeatable); mutually exclusive with `--include-tests` / `--exclude-tests` |
| `--mode shadow\|enforce` | **`shadow`** surfaces findings without failing the exit code for policy violations; **`enforce`** applies normal gating (default **`enforce`**) |
| `--level error\|warning` | Optional reporting level override for the review run |
| `--bug-hunt` | Enable exploratory / bug-hunt style heuristics in the review pipeline |
| `--include-noise`, `--suppress-noise` | Keep or suppress known low-signal findings |
| `--json` | Emit a `ReviewReport` JSON file |
| `--out <path>` | JSON output path (only valid together with **`--json`**) |
| `--score-only` | Print just the reward delta integer |
| `--no-tests` | Skip the TDD gate |
| `--fix` | Apply Ruff autofixes, then rerun the review |
| `--interactive` | Prompt for scope decisions before execution |

## Invalid combinations

The command validates several incompatible flag mixes before the review pipeline runs.

The Typer entrypoint validates **review flags** first: it raises **`typer.BadParameter`** when **`--include-tests`** is combined with **`--exclude-tests`**, or when **`--focus`** is combined with **`--include-tests`** or **`--exclude-tests`**. **Request validation** then rejects incompatible output modes (**`--json`** with **`--score-only`**, or **`--out`** without **`--json`**), and rules for **conflicting targeting styles** reject mixing positional **`FILES...`** with **`--scope`** or **`--path`**. Those deeper checks still surface as **`typer.BadParameter`** with the messages below.

- **Positional `FILES...` with `--scope` or `--path`**: when you pass explicit paths, do not also pass **`--scope`** or **`--path`** (those options apply only to auto-discovery). Runtime error: **`Choose positional files or auto-scope controls, not both.`**
- **`--focus` with `--include-tests` or `--exclude-tests`**: use **`--focus`** *or* the include/exclude test flags, not both. Runtime error: **`Cannot combine --focus with --include-tests or --exclude-tests`**
- **`--include-tests` with `--exclude-tests`**: pick at most one test inclusion mode. Runtime error: **`Cannot use both --include-tests and --exclude-tests`**
- **`--out` without `--json`**: **`--out`** is accepted only when **`--json`** is also set. Runtime error: **`Use --out together with --json.`**
- **`--json` with `--score-only`**: do not combine JSON report output with score-only mode (**`Use either --json or --score-only, not both.`**).

**Supported targeting:** either pass **positional file paths** for a fixed review set (the pipeline still only reviews Python sources it accepts, such as **`.py`** / **`.pyi`**), or omit files and use **`--scope`** / **`--path`** (and related test flags) for auto-discovery — do not mix positional paths with **`--scope`** or **`--path`**.

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

- [Code review ledger](/bundles/code-review/ledger/)
- [Code review rules](/bundles/code-review/rules/)
- [Code review module guide](/modules/code-review/)
