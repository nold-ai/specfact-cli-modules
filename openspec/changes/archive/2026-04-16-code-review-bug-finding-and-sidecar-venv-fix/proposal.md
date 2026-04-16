## Why

External repo validation (crewAI, gpt-researcher, and 8 OSS baseline repos) revealed two concrete tool gaps: the code review module produces no bug-finding signal on repos that don't use icontract, and the sidecar route extractor inflates route counts by scanning its own installed venv. Both blockers limit the tool's usefulness on arbitrary Python codebases.

## What Changes

- **Semgrep bug-finding rules**: Add a `bugs.yaml` semgrep config alongside the existing `clean_code.yaml`, covering Python security patterns, unsafe access, known bug-prone patterns. Wire it as a second semgrep pass in the runner.
- **CrossHair timeout increase + bug-hunt mode**: Expose a `--bug-hunt` flag on `specfact code review run` that raises `--per_path_timeout` from 2s to 10s and total timeout from 30s to 120s, giving CrossHair enough budget to find counterexamples in type-annotated code without icontract.
- **MISSING_ICONTRACT suppression on external repos**: When a reviewed codebase has zero icontract usage, suppress `MISSING_ICONTRACT` warnings rather than emitting one per public function. Auto-detect by scanning the reviewed files for any `@require`/`@ensure` import; if none found, omit the rule entirely for that run.
- **Sidecar venv self-scan fix**: Exclude `.specfact/` from the route extraction scan path in all framework extractors (`FlaskExtractor`, `FastAPIExtractor`, `DjangoExtractor`). Currently the sidecar installs deps into `.specfact/venv` then scans the full repo tree, picking up the installed framework's own source (gpt-researcher: 25,947 reported routes vs 19 real).
- **Review enforcement mode**: Add `--mode shadow` and `--mode enforce` on `specfact code review run`. **Shadow** runs the full tool chain and emits findings (human table and/or JSON) but **never fails the process** (`ci_exit_code` and process exit are `0`) so CI or local hooks can log signal without blocking. **Enforce** preserves today’s governed exit behaviour (blocking findings still yield a non-zero exit). Default is **enforce** for backward compatibility.
- **Review scope facets**: Add repeatable `--focus` options (`source`, `tests`, `docs`) to restrict which Python files are reviewed after auto-scope or positional resolution. **Source** means non-test application Python (same class of paths as the default when tests are excluded). **Tests** means paths that match the existing test-path heuristic (`tests` path segment). **Docs** means Python files under a top-level or nested `docs/` directory segment (e.g. `docs/conf.py`). Multiple `--focus` values union their file sets. This complements (and must be reconciled with) existing `--include-tests` / `--exclude-tests`; passing conflicting combinations SHALL be rejected with a clear CLI error.
- **Review severity floor**: Add `--level error` and `--level warning` to control which findings appear in output and participate in scoring/verdict. **`error`** keeps only `severity="error"` findings. **`warning`** keeps `error` and `warning` and drops `info`. Omitted `--level` keeps all severities (current behaviour).
- **Mandatory tool dependencies + graceful skips**: The code-review module manifest (`packages/specfact-code-review/module-package.yaml` `pip_dependencies`) SHALL list every **external** CLI and Python package required to execute the full review pipeline (Ruff, Radon, Semgrep, basedpyright, Pylint, CrossHair, pytest/pytest-cov for the TDD gate, plus any new runners such as a second Semgrep pass). At **runtime**, before invoking each external tool, the runner SHALL detect availability (`shutil.which` for CLIs; import/subprocess probe for pytest as appropriate). If a tool is missing, that step SHALL be **skipped** (no partial subprocess), and the run SHALL record **exactly one** `ReviewFinding` with `category="tool_error"` whose message states that **review checks for that tool were skipped** because it is not installed, and names the **pip package** from the manifest users should install. The AST clean-code pass remains in-process Python and does not require a separate CLI dependency row.

## Capabilities

### New Capabilities

- `code-review-bug-finding`: Semgrep security/bug rules pass and CrossHair bug-hunt mode — a second analysis layer focused on detecting actual bugs rather than clean-code style issues.
- `code-review-tool-dependencies`: Declared pip dependencies match all external review tools; missing tools produce explicit skip findings instead of opaque failures.

### Modified Capabilities

- `contract-runner`: CrossHair timeout parameters increase for bug-hunt mode; MISSING_ICONTRACT auto-suppressed when no icontract usage is detected in the reviewed files.
- `clean-code-policy-pack`: Second semgrep config (`bugs.yaml`) added alongside `clean_code.yaml`; semgrep runner gains a second config load pass.
- `review-run-command`: New `--bug-hunt`, `--mode`, `--focus`, and `--level` flags wired through `ReviewRunRequest` and `run_command`; file resolution and report rendering respect focus and severity floor; enforcement mode overrides exit code in shadow.
- `review-cli-contracts`: CLI contract scenarios extended for the new flags and guardrails.

## Impact

- `packages/specfact-code-review/src/specfact_code_review/tools/contract_runner.py` — CrossHair timeout params, MISSING_ICONTRACT suppression logic
- `packages/specfact-code-review/src/specfact_code_review/tools/semgrep_runner.py` — second config pass for `bugs.yaml`
- `packages/specfact-code-review/src/specfact_code_review/run/commands.py` — `--bug-hunt`, `--mode`, `--focus`, `--level`; extend `ReviewRunRequest`; apply focus to resolved files, severity filter and shadow exit override before render
- `packages/specfact-code-review/src/specfact_code_review/review/commands.py` — Typer options and validation for new flags; thread into `run_command`
- `packages/specfact-code-review/src/specfact_code_review/run/runner.py` — pass `bug_hunt` through to tool steps; TDD gate skip messages when pytest/cov unavailable; after tools produce raw findings, apply `--level` filtering and call `score_review` on the filtered list so `ReviewReport` fields stay aligned; apply `--mode shadow` exit override on the assembled report
- `packages/specfact-code-review/src/specfact_code_review/tools/*.py` — early availability checks; standardized skip `tool_error` messages (replace misleading “parse output” errors when the executable is missing)
- `packages/specfact-code-review/module-package.yaml` — audit `pip_dependencies` against the canonical tool map; add any missing packages when new runners ship
- `tests/cli-contracts/specfact-code-review-run.scenarios.yaml` — scenarios for mode, focus, level, and conflict errors
- `packages/specfact-code-review/.semgrep/bugs.yaml` — new file
- `packages/specfact-codebase/` — sidecar framework extractors: exclude `.specfact/` from scan paths
- Versioning: patch bump `specfact-codebase` for the sidecar fix; patch or minor bump `specfact-code-review` when behaviour and manifest changes ship (tooling + CLI surface)

## Source Tracking

- **GitHub Issue**: [#174](https://github.com/nold-ai/specfact-cli-modules/issues/174)
- **Repository**: nold-ai/specfact-cli-modules
- **Parent Feature**: [#175](https://github.com/nold-ai/specfact-cli-modules/issues/175) — Code review external repo quality and bug finding
- **Epic**: [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162)
- **OpenSpec change folder**: `code-review-bug-finding-and-sidecar-venv-fix`
- **Change order**: `openspec/CHANGE_ORDER.md` — Pending → “Code review and sidecar validation improvements”
