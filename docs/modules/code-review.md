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

`specfact code review run` now executes the governed review pipeline end to end.

### Command shape

```bash
specfact code review run [OPTIONS] [FILES...]
```

Options:

- `--json`: write the governed `ReviewReport` JSON payload to a file
- `--out PATH`: override the JSON output file path used with `--json`
- `--score-only`: print only the integer `reward_delta`
- `--fix`: apply Ruff autofixes and re-run the review before printing results
- `--no-tests`: skip the targeted TDD gate
- `--scope changed|full`: choose changed-only or full-repository auto-discovery
  when positional files are omitted
- `--path PATH`: repeatable repo-relative subtree filter for auto-discovered
  review targets
- `--include-tests/--exclude-tests`: include or exclude changed test files when
  review scope is auto-detected from `git diff`
- `--include-noise/--suppress-noise`: include or suppress known low-signal
  findings such as test-scope contract noise
- `--interactive`: ask whether changed test files should be included before
  auto-detected review runs

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

Positional `FILES...` cannot be mixed with `--scope` or `--path`. Choose one
targeting style per invocation.

With default noise suppression, the review also hides known low-signal test
findings such as:

- `contract_runner MISSING_ICONTRACT` on test functions
- selected `basedpyright` import/attribute findings in tests
- `pylint W0212` when tests intentionally exercise internal helpers
- `pylint R0801` duplicate-code reports that are better treated as advisory

### Exit codes

- `0`: `PASS` or `PASS_WITH_ADVISORY`
- `1`: `FAIL`
- `2`: invalid CLI usage, such as a missing file path or incompatible options

### Output modes

Default output renders findings grouped by category, then prints verdict, CI
exit code, score, reward delta, and the review summary.

During long-running reviews, the CLI now emits step progress to stderr so users
can see the current phase without breaking stdout-oriented contracts like the
final `--json` output path.

`--json` writes the `ReviewReport` envelope to `review-report.json` by default.
Use `--out` to override the file path:

```bash
specfact code review run --json tests/fixtures/review/clean_module.py
specfact code review run --json --out /tmp/review-report.json packages/specfact-code-review/src/specfact_code_review/run/commands.py
specfact code review ledger update --from /tmp/review-report.json
```

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
| `get-modify-same-method` | `clean_code` |
| `unguarded-nested-access` | `clean_code` |
| `cross-layer-call` | `architecture` |
| `module-level-network` | `architecture` |
| `print-in-src` | `architecture` |

Representative anti-patterns covered by the ruleset:

- methods that both read state and mutate it
- direct nested attribute access like `obj.config.value`
- repository and HTTP client calls in the same function
- module-level network client instantiation
- `print(...)` in source code

Additional behavior:

- only the provided file list is considered
- semgrep rule IDs emitted with path prefixes are normalized back to the governed rule IDs above
- malformed output or a missing Semgrep executable yields a single `tool_error` finding

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
reward ledger and keep it small enough for AI session context injection.

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
