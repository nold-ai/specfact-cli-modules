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

The pipeline reviews **`.py`** and **`.pyi`** only. The **`--focus docs`** facet selects Python files whose path contains a **`docs/`** directory segment (for example tooling beside the Jekyll site), not Markdown documentation pages. For published-site link, front matter, and command-example checks on the modules docs tree, run **`python scripts/check-docs-commands.py`** in this repository (see CI and contributing docs).

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

### Auto-discovered scope (omit positional files)

```bash
# Tracked + untracked changes; tests excluded by default for auto-scope
specfact code review run --scope changed

# Same, with bug-hunt heuristics on the discovered file set
specfact code review run --scope changed --bug-hunt

# Full index, limited to one package (repeat --path for more repo-relative prefixes)
specfact code review run --scope full --path packages/specfact-code-review

# Package sources plus that package’s unit tests
specfact code review run --scope full --path packages/specfact-code-review --path tests/unit/specfact_code_review

# Warnings dropped before scoring (affects JSON, verdict text, and ci_exit_code)
specfact code review run --scope changed --level warning

# Longer CrossHair budgets for exploratory bug-hunt pass (with explicit files)
specfact code review run --bug-hunt --json --out /tmp/review-bughunt.json packages/specfact-code-review/src/specfact_code_review/run/commands.py
```

### Shadow mode and JSON to a file

**`--mode shadow`** runs the full toolchain but forces process exit code **`0`** and JSON **`ci_exit_code`** **`0`** so callers can ingest reports without failing a step; **`overall_verdict`** still reflects the real outcome.

```bash
specfact code review run --scope changed --mode shadow --json --out /tmp/review-report.json
```

### `--focus` facets (repeatable)

Use **`--focus`** with **`source`**, **`tests`**, and/or **`docs`** (union of facets, then intersect with scope). Do not combine **`--focus`** with **`--include-tests`** or **`--exclude-tests`**.

```bash
specfact code review run --scope changed --focus tests
specfact code review run --scope full --path packages/specfact-code-review --focus source
specfact code review run --scope full --focus docs
```

### Positional files (explicit Python paths)

Do not pass **`--scope`** or **`--path`** when **`FILES...`** are present.

```bash
specfact code review run --json --out /tmp/review-report.json packages/specfact-code-review/src/specfact_code_review/run/commands.py
specfact code review run --score-only packages/specfact-code-review/src/specfact_code_review/run/commands.py
specfact code review run --fix packages/specfact-code-review/src/specfact_code_review/run/commands.py
specfact code review run --no-tests packages/specfact-code-review/src/specfact_code_review/run/commands.py
```

### Noise and interactive test inclusion

```bash
specfact code review run --scope changed --include-noise
specfact code review run --scope changed --suppress-noise
specfact code review run --scope changed --interactive
```

## Bundle-owned resources

The review pipeline uses rules, skills, and policy payloads shipped with the installed Code Review bundle. Those assets are bundle-owned and should be refreshed through supported bundle and IDE setup flows rather than legacy core-owned paths.

## Related

- [Code review ledger](/bundles/code-review/ledger/)
- [Code review rules](/bundles/code-review/rules/)
- [Code review module guide](/modules/code-review/)
