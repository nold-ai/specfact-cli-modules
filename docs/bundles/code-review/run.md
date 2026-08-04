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
| `--focus <facet>` | Limit auto-discovered scope to **`source`**, **`tests`**, **`docs`**, and/or **`simplify`** (repeatable); mutually exclusive with `--include-tests` / `--exclude-tests` |
| `--enforcement full\|changed\|shadow` | **`full`** blocks on any blocking finding in reviewed files; **`changed`** blocks only blocking findings on changed lines (default **`changed`**); **`shadow`** records evidence and never blocks |
| `--mode shadow\|enforce` | Deprecated compatibility alias: **`--mode enforce`** maps to **`--enforcement full`** and **`--mode shadow`** maps to **`--enforcement shadow`** |
| `--level error\|warning` | Optional reporting level override before scoring: **`error`** keeps errors only (drops warnings and info); **`warning`** keeps errors and warnings (drops info only); omit to keep all severities (JSON, verdict, and `ci_exit_code` use the filtered list) |
| `--bug-hunt` | Enable exploratory / bug-hunt style heuristics in the review pipeline |
| `--include-noise`, `--suppress-noise` | Keep or suppress known low-signal findings |
| `--json` | Emit a `ReviewReport` JSON file |
| `--out <path>` | JSON output path (only valid together with **`--json`**) |
| `--score-only` | Print just the reward delta integer |
| `--no-tests` | Skip the TDD gate |
| `--fix` | Apply Ruff autofixes, then rerun the review |
| `--preview-fixes` | For **`--focus simplify`**, compute non-mutating patch evidence for supported safe-mechanical simplification fixers |
| `--with-mutation` | For **`--focus simplify`**, record opt-in mutation proof evidence for cleanup candidates; unavailable tooling is inconclusive |
| `--requirements-evidence <path>` | Attach a finalized schema-v2 Requirements proof as independent provenance in the review JSON; it does not affect the review verdict or exit code |
| `--interactive` | Prompt for scope decisions before execution |
| `--instructions` | Print AI-facing simplify / clean-code workflow instructions and exit without running review |

## Invalid combinations

The command validates several incompatible flag mixes before the review pipeline runs.

The Typer entrypoint validates **review flags** first: it raises **`typer.BadParameter`** when **`--include-tests`** is combined with **`--exclude-tests`**, or when **`--focus`** is combined with **`--include-tests`** or **`--exclude-tests`**. **Request validation** then rejects incompatible output modes (**`--json`** with **`--score-only`**, or **`--out`** without **`--json`**), and rules for **conflicting targeting styles** reject mixing positional **`FILES...`** with **`--scope`** or **`--path`**. Those deeper checks still surface as **`typer.BadParameter`** with the messages below.

- **Positional `FILES...` with `--scope` or `--path`**: when you pass explicit paths, do not also pass **`--scope`** or **`--path`** (those options apply only to auto-discovery). Runtime error: **`Choose positional files or auto-scope controls, not both.`**
- **`--focus` with `--include-tests` or `--exclude-tests`**: use **`--focus`** *or* the include/exclude test flags, not both. Runtime error: **`Cannot combine --focus with --include-tests or --exclude-tests`**
- **`--include-tests` with `--exclude-tests`**: pick at most one test inclusion mode. Runtime error: **`Cannot use both --include-tests and --exclude-tests`**
- **`--out` without `--json`**: **`--out`** is accepted only when **`--json`** is also set. Runtime error: **`Use --out together with --json.`**
- **`--json` with `--score-only`**: do not combine JSON report output with score-only mode (**`Use either --json or --score-only, not both.`**).
- **`--preview-fixes` with `--fix`**: preview is non-mutating and cannot be combined with write mode. Runtime error: **`Cannot combine --preview-fixes with --fix.`**
- **`--preview-fixes` without simplify focus**: preview evidence is scoped to cleanup findings. Runtime error: **`Use --preview-fixes only with --focus simplify.`**
- **`--with-mutation` without simplify focus**: mutation proof is scoped to cleanup candidates. Runtime error: **`Use --with-mutation only with --focus simplify.`**

**Supported targeting:** either pass **positional file paths** for a fixed review set (the pipeline still only reviews Python sources it accepts, such as **`.py`** / **`.pyi`**), or omit files and use **`--scope`** / **`--path`** (and related test flags) for auto-discovery — do not mix positional paths with **`--scope`** or **`--path`**.

## Requirements proof context

Use **`--requirements-evidence <path>`** to retain the provenance of a completed
Requirements proof beside the review result. The input must be a complete,
readable finalized proof accepted by the runtime loader: **`schema_version:
"2"`**, **`execution_proof.run_stage: "final"`**, valid SHA-256
**`mapping_digest`** and **`plan_digest`** values, a 40- or 64-character
hexadecimal **`execution_proof.source_ref`**, and a **`gate_decision`** of
`pass` or `fail`.
The resulting `ReviewReport` uses schema version **`1.5`** and records the
proof path, content digest, mapping and plan digests, source revision, and the
Requirements gate decision under `requirements_evidence`.

This is context only: Code Review does not reinterpret the Requirements proof,
and the Requirements decision neither changes the review verdict nor its exit
code. A finalized Requirements failure can therefore remain visible as
provenance while an otherwise clean review reports its own independent result.

```bash
specfact code review run --json --out .specfact/code-review.json \
  --requirements-evidence artifacts/requirements-evidence.json \
  packages/specfact-code-review/src/specfact_code_review/run/commands.py
```

## Examples

### Auto-discovered scope (omit positional files)

```bash
# Tracked + untracked changes; tests excluded by default for auto-scope
specfact code review run --scope changed

# Same, with bug-hunt heuristics on the discovered file set
specfact code review run --scope changed --enforcement changed --bug-hunt

# Full index, limited to one package (repeat --path for more repo-relative prefixes)
specfact code review run --scope full --path packages/specfact-code-review

# Package sources plus that package’s unit tests
specfact code review run --scope full --path packages/specfact-code-review --path tests/unit/specfact_code_review

# Errors only before scoring — warnings and info omitted from JSON, verdict, and ci_exit_code
specfact code review run --scope changed --level error

# Longer CrossHair budgets for exploratory bug-hunt pass (with explicit files)
specfact code review run --enforcement changed --bug-hunt --json --out /tmp/review-bughunt.json packages/specfact-code-review/src/specfact_code_review/run/commands.py
```

### Enforcement modes and JSON to a file

**`--enforcement changed`** is the default for the CLI: it writes every finding to JSON, but only blocking findings on changed lines fail the process. Legacy findings elsewhere in touched files remain visible in **`findings`** plus **`enforcement_summary`** evidence.

**`--enforcement full`** is the strictest mode: any blocking finding in the reviewed files fails the process, including existing issues on untouched lines.

**`--enforcement shadow`** runs the full toolchain but forces process exit code **`0`** and JSON **`ci_exit_code`** **`0`** so callers can ingest reports without failing a step; **`overall_verdict`** still reflects the real outcome. The older **`--mode shadow`** form remains available as a compatibility alias.

```bash
specfact code review run --scope changed --enforcement changed --json --out /tmp/review-report.json
specfact code review run --scope full --enforcement full --json --out /tmp/review-full.json
specfact code review run --scope changed --enforcement shadow --json --out /tmp/review-shadow.json
```

### `--focus` facets (repeatable)

Use **`--focus`** with **`source`**, **`tests`**, **`docs`**, and/or **`simplify`** (union of facets, then intersect with scope). Do not combine **`--focus`** with **`--include-tests`** or **`--exclude-tests`**. The **`simplify`** facet produces simplification-focused reports: advisory **`ai_bloat`** findings plus high-confidence **`dry`** and **`kiss`** findings that carry deterministic metadata such as **`rewrite_hint`**, **`canonical_pattern`**, **`intent_key`**, **`estimated_deletion_lines`**, and **`related_locations`**. Simplification-focused JSON also includes **`cleanup_forecast`**, **`signal_trace`**, **`preserve_reasons`**, and **`remediation_packet`** fields when available.

```bash
specfact code review run --scope changed --focus tests
specfact code review run --scope full --path packages/specfact-code-review --focus source
specfact code review run --scope full --focus docs
specfact code review run --scope changed --enforcement shadow --focus simplify --preview-fixes --json --out .specfact/code-review.json
specfact code review run --scope changed --enforcement shadow --focus simplify --with-mutation --json --out .specfact/code-review.json
```

Use the canonical `.specfact/code-review.json` path unless every consumer in your workflow has been updated to read a custom simplify report path.

### AI instructions fallback

When an IDE does not support bundled prompts or skills, print the same guided simplify workflow for an AI assistant:

```bash
specfact code review run --instructions
```

The output explains how to remove AI bloat and apply clean-code simplifications using SpecFact evidence, including `cleanup_forecast`, `safe_mechanical`, `needs_tests`, `design_judgment`, `preserve`, `remediation_packet`, patch previews, conservative keep/skip defaults, and per-file validation. It also tells assistants how to handle clean PR branches where `--scope changed` has no worktree files: find branch-delta Python files with a base-ref diff such as `git diff --name-only <base-ref>...HEAD -- '*.py' '*.pyi'`, review those files as explicit positional files, and treat findings without `guidance_kind` as unguided advisories rather than auto-fix input. `ai_bloat` findings are cleanup signals, not proof of AI authorship.

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

The built-in `specfact/ai-bloat-patterns` policy pack is parallel to `specfact/clean-code-principles`. It maps advisory `ai_bloat` rules to the `ai_bloat` principle, emits `severity=info`, and stays score-neutral so simplification candidates do not block commits. Omit `--level` when producing the JSON report for `/specfact.08-simplify`; `--level error` intentionally filters info-level findings out of the command report.

Use `--focus simplify` when producing the IDE simplification queue:

```bash
specfact code review run --scope changed --enforcement shadow --focus simplify --preview-fixes --json --out .specfact/code-review.json
```

Simplify-focused reports keep advisory `ai_bloat` findings plus high-confidence `dry` and `kiss` findings that include deterministic simplification metadata. Metadata fields such as `rewrite_hint`, `canonical_pattern`, `intent_key`, `estimated_deletion_lines`, `related_locations`, `signal_trace`, `preserve_reasons`, and `remediation_packet` are additive; legacy consumers can keep reading the original finding fields. The report-level `cleanup_forecast` summarizes reviewed LOC, estimated deletion ranges, guidance-kind totals, normalized AI-bloat density, weighted bloat points, and cleanup-yield LOC per KLOC. Simplification findings remain score-neutral; enforce mode blocks only unresolved safe-mechanical cleanup candidates.

## Related

- [Code review ledger](/bundles/code-review/ledger/)
- [Code review rules](/bundles/code-review/rules/)
- [Code review module guide](/modules/code-review/)
