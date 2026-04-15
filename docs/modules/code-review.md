---
layout: default
title: Code review module
nav_order: 10
permalink: /modules/code-review/
keywords: [code-review, module, review, quality, analysis]
audience: [solo, team, enterprise]
expertise_level: [intermediate, advanced]
---

# specfact-code-review module notes

## Review run command

`specfact code review run` executes the governed review pipeline end to end.

The **bundle run guide** at [Code review run](/bundles/code-review/run/) lists
the same public flags in a compact table, documents **invalid flag
combinations**, and matches the Typer surface. This section keeps module-level
detail (tooling behavior, exit codes, examples).

### Command shape

```bash
specfact code review run [OPTIONS] [FILES...]
```

Options (aligned with `specfact code review run --help`):

- `--scope changed|full`: choose changed-only or full-repository auto-discovery
  when positional files are omitted
- `--path PATH`: repeatable repo-relative subtree filter for auto-discovered
  review targets
- `--include-tests` / `--exclude-tests`: include or exclude changed test files when
  review scope is auto-detected from `git diff`
- `--focus`: repeatable facet filter applied after scope resolution; values are
  `source` (non-test, non-docs Python), `tests` (paths with a `tests/` segment),
  and `docs` (Python under a `docs/` directory segment). Multiple `--focus`
  values **union** their file sets, then intersect with the resolved scope. When
  any `--focus` is set, **`--include-tests` and `--exclude-tests` are rejected**
  (use focus alone to express test intent)
- `--mode shadow|enforce`: **enforce** (default) keeps today’s non-zero process
  exit when the governed report says the run failed; **shadow** still runs the
  full toolchain and preserves `overall_verdict` in JSON, but forces
  `ci_exit_code` and the process exit code to `0` so CI or hooks can log signal
  without blocking
- `--level error|warning`: drop findings below the chosen severity **before**
  scoring and report construction so JSON, tables, score, verdict, and
  `ci_exit_code` all match the filtered list. Omit to keep all severities
- `--bug-hunt`: enable the bug-hunt pass (CrossHair uses longer budgets: per-path
  timeout **10s**, subprocess budget **120s**; other tools keep normal speed)
- `--include-noise` / `--suppress-noise`: include or suppress known low-signal
  findings such as test-scope contract noise
- `--json`: emit a `ReviewReport` JSON file (defaults to **`review-report.json`**
  in the working directory when **`--out`** is omitted)
- `--out PATH`: JSON output path (**only valid together with `--json`**)
- `--score-only`: print only the integer `reward_delta`
- `--no-tests`: skip the targeted TDD gate
- `--fix`: apply Ruff autofixes and re-run the review before printing results
- `--interactive`: ask whether changed test files should be included before
  auto-detected review runs

### Invalid combinations

The command rejects incompatible mixes (same rules as the bundle run guide): Typer raises **`BadParameter`** from **`_resolve_review_run_flags()`** for **`--include-tests`** with **`--exclude-tests`**, and for **`--focus`** with **`--include-tests`** or **`--exclude-tests`**; other pairings are enforced in **`run_command()`** via **`_validate_review_request()`**, **`_raise_if_targeting_styles_conflict()`**, and related helpers.

- **Positional `FILES...` with `--scope` or `--path`**: choose explicit files **or**
  auto-scope controls, not both.
- **`--focus` with `--include-tests` or `--exclude-tests`**: use **`--focus`** *or*
  the include/exclude flags, not both.
- **`--include-tests` with `--exclude-tests`**: pick at most one test inclusion mode.
- **`--out` without `--json`**: **`--out`** is accepted only when **`--json`** is also set.
- **`--json` with `--score-only`**: pick one, not both (**`--json`** cannot be used with **`--score-only`**).

When `FILES` is omitted, the command falls back to:

```bash
git diff HEAD --name-only
git ls-files --others --exclude-standard
```

Only existing Python files from tracked or untracked workspace changes are
reviewed. Test files under `tests/` are excluded by default for auto-detected
review scope unless you pass `--include-tests` or answer yes in
`--interactive` mode. Explicit `--path tests/...` filters count as intentional
targeting and keep matching tests in scope even with the default test
exclusion.

Use `--scope full` to review the governed repository file set instead of just
current changes:

```bash
specfact code review run --scope full
```

Use repeatable `--path` filters to limit either scope to one package or a
focused source-plus-test slice:

```bash
specfact code review run --scope full --path packages/specfact-code-review
specfact code review run --scope changed --path packages/specfact-code-review --path tests/unit/specfact_code_review
```

Positional `FILES...` cannot be mixed with **`--scope`** or **`--path`** (see
**Invalid combinations** above).

With default noise suppression, the review also hides known low-signal test
findings such as:

- `contract_runner MISSING_ICONTRACT` on test functions
- selected `basedpyright` import/attribute findings in tests
- `pylint W0212` when tests intentionally exercise internal helpers
- `pylint R0801` duplicate-code reports that are better treated as advisory

### Exit codes

- `0`: `PASS` or `PASS_WITH_ADVISORY`, or any outcome under **`--mode shadow`**
  (shadow forces success at the process level even when `overall_verdict` is
  `FAIL`)
- `1`: `FAIL` under default **enforce** semantics
- `2`: invalid CLI usage, such as a missing file path or incompatible options

### Output modes

Default output renders findings grouped by category, then prints verdict, CI
exit code, score, reward delta, and the review summary.

During long-running reviews, the CLI now emits step progress to stderr so users
can see the current phase without breaking stdout-oriented contracts like the
final `--json` output path.

With **`--json`**, the `ReviewReport` envelope is written to **`review-report.json`**
in the working directory by default; use **`--out`** only together with
**`--json`** to pick another path.

```bash
specfact code review run --json --out /tmp/review-report.json packages/specfact-code-review/src/specfact_code_review/run/commands.py
specfact code review ledger update --from /tmp/review-report.json
```

```bash
specfact code review run --json packages/specfact-code-review/src/specfact_code_review/run/commands.py
specfact code review ledger update --from review-report.json
```

The second block writes JSON next to your cwd as **`review-report.json`**; pass
that same path into **`ledger update --from`**.

`--score-only` is intended for lightweight CI integration:

```bash
specfact code review run --score-only packages/specfact-code-review/src/specfact_code_review/run/commands.py
```

`--fix` applies Ruff-backed autofixes before running the final review report:

```bash
specfact code review run --fix packages/specfact-code-review/src/specfact_code_review/run/commands.py
```

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

### Semgrep runner

`specfact_code_review.tools.semgrep_runner.run_semgrep(files)` executes:

```bash
semgrep --config packages/specfact-code-review/.semgrep/clean_code.yaml --json <files...>
```

Custom rule mapping:

| Semgrep rule | ReviewFinding category |
| --- | --- |
| `banned-generic-public-names` | `naming` |
| `swallowed-exception-pattern` | `clean_code` |
| `get-modify-same-method` | `clean_code` |
| `unguarded-nested-access` | `clean_code` |
| `cross-layer-call` | `architecture` |
| `module-level-network` | `architecture` |
| `print-in-src` | `architecture` |

Representative anti-patterns covered by the ruleset:

- methods that both read state and mutate it
- public symbols that use banned generic names like `data` or `process`
- swallowed exceptions that hide an underlying failure path
- direct nested attribute access like `obj.config.value`
- repository and HTTP client calls in the same function
- module-level network client instantiation
- `print(...)` in source code

Additional behavior:

- only the provided file list is considered
- semgrep rule IDs emitted with path prefixes are normalized back to the governed rule IDs above
- malformed output, a missing `results` list, or a missing Semgrep executable yields a single `tool_error` finding

### Semgrep bug-rules pass

After the clean-code Semgrep pass, the orchestrator runs
`specfact_code_review.tools.semgrep_runner.run_semgrep_bugs(files)`, which uses
`packages/specfact-code-review/.semgrep/bugs.yaml` when present. Findings are
mapped to `security` or `correctness`. If the config file is missing, the pass
is skipped with no error.

### Contract runner

`specfact_code_review.tools.contract_runner.run_contract_check(files, *, bug_hunt=False)` combines two
contract-oriented checks:

1. an AST scan for public functions missing `@require` / `@ensure`
2. a CrossHair fast pass

AST scan behavior:

- only public module-level and class-level functions are checked
- functions prefixed with `_` are treated as private and skipped
- the AST scan for `MISSING_ICONTRACT` runs only when a batch-level package/repo
  scan root imports `icontract` (`from icontract …` or `import icontract`).
  Reviewed files in a package that uses icontract are scanned even when the
  changed file itself does not import icontract
- missing icontract decorators become `contracts` findings with rule
  `MISSING_ICONTRACT` when the scan runs
- unreadable or invalid Python files degrade to a single `tool_error` finding instead
  of raising

CrossHair behavior:

```bash
crosshair check --per_path_timeout 2 <files...>   # default
crosshair check --per_path_timeout 10 <files...>  # with CLI --bug-hunt
```

- CrossHair counterexamples map to `contracts` warnings with tool `crosshair`
- timeouts are skipped so the AST scan can still complete
- missing CrossHair binaries degrade to a single `tool_error` finding
- with **`--bug-hunt`**, the per-path timeout is **10** seconds and the
  subprocess budget is **120** seconds instead of **2** / **30**

Operational note:

- the current development environment includes CrossHair, but installed-user
  environments still need that executable available for the fast pass to run

## Ledger commands

The `specfact-code-review` bundle now includes a reward ledger that persists
review outcomes and exposes a small CLI surface under `specfact code review
ledger`.

### Command flow

Use the governed review report as the canonical input for ledger updates:

```bash
specfact code review run --json --out /tmp/review-report.json
specfact code review ledger update --from /tmp/review-report.json
specfact code review ledger status
specfact code review ledger reset --confirm
```

### Storage behavior

- When `SUPABASE_URL` and `SUPABASE_KEY` are present, the ledger writes review
  runs to `ai_sync.review_runs` and appends ledger snapshots to
  `ai_sync.reward_ledger`.
- The reviewed DDL lives with the bundle at
  `packages/specfact-code-review/src/specfact_code_review/resources/supabase/review_ledger_ddl.sql`
  instead of a repo-root infrastructure folder.
- When Supabase is unavailable or not configured, the bundle falls back to a
  local JSON ledger. In a repository checkout it prefers
  `.specfact/ledger.json`; otherwise it falls back to `~/.specfact/ledger.json`.
- `ledger status` prints coins, pass/block streaks, the last verdict, and the
  top three violation rules seen so far.
- `ledger reset` only clears the local JSON fallback and requires `--confirm`.

### Local module development

If the CLI warns that bundled modules are missing or outdated while you are
testing local bundle changes, refresh the project-scope modules first:

```bash
specfact module init --scope project
```

Then rerun the ledger command from the same repository checkout.

## House rules skill

The `specfact-code-review` bundle can derive a compact house-rules skill from the
reward ledger and keep it small enough for AI session context injection. The
default charter now encodes the clean-code principles directly:

- Naming: use intention-revealing names instead of placeholders.
- KISS: keep functions small, shallow, and narrow in parameters.
- YAGNI: remove unused private helpers and speculative layers.
- DRY: extract repeated function shapes once duplication appears.
- SOLID: keep transport and persistence responsibilities separate.
- TDD + contracts: keep test-first and icontract discipline in the baseline skill.

### Command flow

```bash
specfact code review rules init
specfact code review rules show
specfact code review rules update
```

### Generated files

- `rules init` creates `skills/specfact-code-review/SKILL.md` in the current
  project from the bundled package template (or default content if bundled is unavailable),
  does not touch `CLAUDE.md`, and can optionally install one canonical IDE target
  via `--ide <claude|codex|cursor|vibe>`.
- **Cursor (special case)**: `.cursor/rules/house_rules.mdc` — rules format for
  auto-attachment when `--ide cursor` is chosen.
- **SKILL.md compatible IDEs**: `.claude/skills/specfact-code-review/SKILL.md`,
  `.codex/skills/specfact-code-review/SKILL.md`, `.vibe/skills/specfact-code-review/SKILL.md`
  when their matching `--ide` value is chosen.
- `rules show` prints the current `SKILL.md` content and suggests `rules init`
  when the file is missing.
- `rules update` reads the last 20 ledger runs, surfaces rule IDs with at least
  three hits in the auto-managed `TOP VIOLATIONS` section, prunes stale entries
  that have disappeared for 10 runs, and increments the skill version header.
- The updater preserves the curated `DO` and `DON'T` sections, updates the
  `Updated:` timestamp, and enforces a 35-line hard cap by removing the
  lowest-frequency violation entries first.
- `rules update` refreshes only canonical IDE targets already installed in the
  project, or a single explicit target when `--ide` is supplied.

## Review orchestration

`specfact_code_review.run.runner.run_review(
files,
no_tests=False,
include_noise=False,
progress_callback=None,
bug_hunt=False,
review_level=None,
review_mode="enforce",
)` orchestrates the bundle runners in this order:

1. Ruff
2. Radon
3. Semgrep (clean-code ruleset)
4. Semgrep bug rules (`.semgrep/bugs.yaml`, skipped if absent)
5. AST clean-code checks
6. basedpyright
7. pylint
8. contract runner (AST + CrossHair; optional bug-hunt timeouts)
9. TDD gate, unless `no_tests=True`

When `SPECFACT_CODE_REVIEW_PR_MODE=1` is present, the runner also evaluates a
bundle-local advisory PR checklist from `SPECFACT_CODE_REVIEW_PR_TITLE`,
`SPECFACT_CODE_REVIEW_PR_BODY`, and `SPECFACT_CODE_REVIEW_PR_PROPOSAL` without
adding a new CLI flag.

The merged findings are then scored into a governed `ReviewReport`.

Representative programmatic use:

```python
from pathlib import Path

from specfact_code_review.run.runner import run_review

report = run_review(
    [Path("src/app.py")],
    no_tests=False,
    include_noise=False,
    bug_hunt=True,
    review_level="error",
    review_mode="shadow",
)
```

## Bundled policy pack

The bundle now ships `specfact/clean-code-principles` as a resource payload at:

- `packages/specfact-code-review/resources/policy-packs/specfact/clean-code-principles.yaml`
- `packages/specfact-code-review/src/specfact_code_review/resources/policy-packs/specfact/clean-code-principles.yaml`

The manifest exposes the clean-code rule IDs directly so downstream policy code
can apply advisory, mixed, or hard modes without a second review-specific
severity schema.

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
