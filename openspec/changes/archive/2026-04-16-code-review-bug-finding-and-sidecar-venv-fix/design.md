## Context

The `specfact-code-review` bundle runs seven analysis tools in sequence (ruff, radon, semgrep, AST, basedpyright, pylint, contract_runner). External-repo validation across 10 Python repos revealed two gaps:

1. **No bug-finding signal on repos without icontract**: CrossHair already runs (`contract_runner.py:112`) but with `--per_path_timeout 2` and a 30s hard cap — too tight to find counterexamples in type-annotated code. Semgrep runs only `clean_code.yaml` rules (style/architecture); no security or bug-pattern rules exist. `MISSING_ICONTRACT` fires on every public function in any repo that hasn't opted into icontract, producing hundreds of low-value warnings that drown real signal.

2. **Sidecar venv self-scan**: All three framework extractors (FastAPI, Flask, Django/DRF) use `search_path.rglob("*.py")` with no path exclusions. The sidecar dependency installer writes into `.specfact/venv/` before extraction runs. Result: the FastAPI extractor on gpt-researcher picked up FastAPI's own source from the venv and reported 25,947 routes (actual: 19). The fix is a single shared exclusion applied at the `rglob` call site.

## Goals / Non-Goals

**Goals:**
- Add a `--bug-hunt` flag to `specfact code review run` that gives CrossHair meaningful budget (10s/path, 120s total)
- Add a `bugs.yaml` semgrep config with Python security/bug rules, wired as a second semgrep pass
- Auto-suppress `MISSING_ICONTRACT` when no `@require`/`@ensure` imports are found in the reviewed files
- Exclude `.specfact/` from all sidecar framework extractor scan paths
- Add `--mode shadow|enforce`, repeatable `--focus source|tests|docs`, and `--level error|warning` with clear CLI validation and stable JSON/human output
- Align `module-package.yaml` `pip_dependencies` with every external review tool and implement runtime skips with explicit `tool_error` messages when a tool is missing

**Non-Goals:**
- Replacing CrossHair with a different symbolic execution engine
- Adding semgrep cloud/registry rules (offline-first; rules must be bundled locally)
- Changing default **enforce** exit semantics for existing users (shadow is strictly opt-in)
- Fixing CrossHair's analysis depth beyond timeout tuning
- Teaching the review runner to lint non-Python doc formats (Markdown/RST) in this change — `--focus docs` applies to **Python files under `docs/`** only

## Decisions

**D1: `bugs.yaml` as a separate semgrep config, not merged into `clean_code.yaml`**

Keeps clean-code rules and bug-finding rules independently evolvable. The semgrep runner already has `find_semgrep_config` that walks parents for `clean_code.yaml` by name — add a parallel `find_semgrep_bugs_config` that looks for `.semgrep/bugs.yaml` and returns `None` (not an error) when absent. Runner calls both; missing `bugs.yaml` is a no-op.

Alternative considered: a single merged config. Rejected — mixing style warnings and bug errors in one file makes the rule set harder to reason about and harder to disable selectively.

**D2: `--bug-hunt` flag rather than a separate command**

`specfact code review run --bug-hunt` passes `bug_hunt=True` through `ReviewRunRequest` → `run_review` → `run_contract_check`. No new command surface, no CLI help restructuring. The flag increases CrossHair timeouts only; all other tools run at normal speed.

Alternative considered: `specfact code review bug-hunt` as a new subcommand. Rejected — unnecessary API surface; `--bug-hunt` is composable with `--scope full`, `--json`, `--out`, etc.

**D3: MISSING_ICONTRACT auto-suppression via import scan, not a flag**

Scan the reviewed file list for any `from icontract import` or `import icontract` statement before running `contract_runner`. If none found, skip `MISSING_ICONTRACT` findings entirely. This is automatic — no user flag needed, works correctly on both internal bundles (which do use icontract) and external repos (which don't).

Alternative considered: `--suppress-missing-contracts` flag. Rejected — requires users to know to pass it; auto-detection is always correct.

**D4: Sidecar exclusion via a shared `_is_excluded_path` helper on `BaseFrameworkExtractor`**

Add `_EXCLUDED_DIR_NAMES = frozenset({".specfact", ".git", "__pycache__", "node_modules"})` and a `_iter_python_files(root: Path)` generator on `BaseFrameworkExtractor` that yields only files whose parts contain no excluded dir name. All three framework extractors replace `search_path.rglob("*.py")` with `self._iter_python_files(search_path)`.

Alternative considered: filtering at the orchestrator level before passing `repo_path` to extractors. Rejected — extractors own the scan, fixing at the source is cleaner and prevents future extractors from re-introducing the bug.

**D5: `--mode` with default `enforce`**

- **`enforce`**: After findings are collected and post-processed (`--level` filter), compute score/verdict/`ci_exit_code` exactly as today; process exit matches `ci_exit_code`.
- **`shadow`**: Same tool execution and same reported findings (after `--level`), but **force** `ci_exit_code = 0` and process exit `0` even when verdict would be `FAIL`. Human and JSON output still show the real `overall_verdict` so operators can see risk while not blocking the pipeline.

Alternative considered: shadow mode hiding failures in JSON. Rejected — that would defeat auditability; only enforcement (exit) is relaxed.

**D6: Repeatable `--focus` as a set union over path facets**

Facets (Python files only, after normal ignore rules):

| Facet | Membership rule |
|-------|-----------------|
| `tests` | `tests` appears in `path.parts` (same heuristic as `_is_test_file`) |
| `docs` | `docs` appears in `path.parts` |
| `source` | suffix `.py`, **not** `tests` facet, **not** `docs` facet |

When `--focus` is passed one or more times, the reviewed file set is the **union** of matching files intersected with the scope-resolved set (positional, `--scope changed|full`, `--path`, etc.). When `--focus` is **omitted**, file resolution stays backward compatible with `--include-tests` / `--exclude-tests` / interactive defaults.

When **any** `--focus` is present, **`--include-tests` and `--exclude-tests` are disallowed** (Typer `BadParameter`) to avoid contradictory intent.

**D7: `--level` as a severity floor on the reported and scored finding list**

Apply **after** all tools finish:

- **`error`**: keep findings where `severity == "error"` only.
- **`warning`**: keep `severity in {"error", "warning"}`; drop `info`.
- **Omitted**: keep all severities (current behaviour).

Recompute `score`, `overall_verdict`, `reward_delta`, and `ci_exit_code` from the **filtered** list so tables, JSON, score line, and exit code stay consistent. Tools still run on the full resolved file set (performance unchanged); only the governance envelope uses the filtered list.

**D8: Typer wiring stays in `review/commands.py`**

New options are declared next to existing `run` flags; parsing/validation errors surface as `typer.BadParameter` with stable messages suitable for cli-contract tests.

**D9: Canonical tool → pip package map owned by the code-review package**

Maintain a single source of truth (Python module or documented table consumed by a test) mapping each **review tool id** to:

- the CLI executable name probed on `PATH` (where applicable), and
- the **PyPI distribution name** declared in `module-package.yaml` `pip_dependencies` (e.g. `crosshair-tool` → executable `crosshair`).

Covered tools for the default pipeline: `ruff`, `radon`, `semgrep`, `basedpyright`, `pylint`, `crosshair`, plus `pytest` / `pytest-cov` for the TDD gate subprocess. **AST clean-code** analysis uses the stdlib and shipped Python code only — no extra `pip_dependencies` row.

When a new runner is added (e.g. second Semgrep pass), the map and `pip_dependencies` MUST be updated in the same change.

**D10: Availability check before subprocess; skip with one `tool_error`**

Each external runner SHALL call a shared helper (e.g. `ensure_tool_available(tool_id, file_path) -> list[ReviewFinding]`) that returns a non-empty list (single finding) when the tool is missing, so the runner returns immediately **without** invoking the tool. This avoids misclassifying `FileNotFoundError` as “parse JSON failed” or similar.

**D11: Standard skip message shape**

Skip findings SHALL use `category="tool_error"`, `rule="tool_error"` (or a dedicated `TOOL_SKIPPED` rule if implementation prefers — spec requires stable filtering by category/tool), `severity="warning"` unless policy elevates missing tools to `error`. The message MUST:

- name the **tool id** (e.g. `ruff`, `semgrep`),
- state that **review checks for that tool were skipped** because it is **not installed** or not on `PATH`,
- cite the **pip package name** from the manifest (e.g. “install `ruff`”).

For pytest invoked via `sys.executable`, treat “pytest not importable” / failed launcher the same way with tool id `pytest` and packages `pytest` / `pytest-cov` as appropriate.

## Risks / Trade-offs

- **CrossHair false positives in bug-hunt mode**: Longer timeouts mean CrossHair explores more paths and may surface `SideEffectDetected` warnings on I/O-heavy functions. Mitigated: `_IGNORED_CROSSHAIR_PREFIXES` already filters `SideEffectDetected`; no change needed.
- **`bugs.yaml` rule maintenance**: Bundled semgrep rules can go stale. Mitigated: keep the initial set small (5–10 high-confidence rules), document in the file header that additions require a PR with test evidence.
- **False confidence when many tools are skipped**: A run may PASS while major tools were skipped. Mitigated: skip findings are visible in human and JSON output; optional follow-up could promote missing-tool severity in enforce mode — out of scope unless added to tasks later.
- **MISSING_ICONTRACT auto-suppression masking real gaps**: If a bundle file imports icontract but only for one function, all other uncovered functions are still flagged. The auto-suppression only fires when zero icontract imports exist — so internal bundles are unaffected.
- **Sidecar exclusion breaking legitimate `.specfact/` source scanning**: No known repo puts application source under `.specfact/`. Risk is negligible.

## Migration Plan

No migrations required. New flags are additive with **defaults preserving today’s behaviour**: `--mode` defaults to `enforce`, `--focus` omitted uses legacy test inclusion rules, `--level` omitted keeps all severities. Sidecar and MISSING_ICONTRACT changes remain backward compatible when not triggered.

Patch version bump on `specfact-codebase` (sidecar bug fix). `specfact-code-review` should receive at least a **patch** bump once shipped (new CLI surface + behaviour). If policy treats bundled `bugs.yaml` as a material artefact, prefer a **minor** bump for the review bundle.

## Open Questions

- Which specific semgrep rules to include in `bugs.yaml` v1? Candidates: `python.lang.security.audit.dangerous-system-call`, `python.lang.correctness.useless-eqeq`, `python.lang.security.audit.hardcoded-password`, `python.lang.correctness.none-not-null`. Needs sign-off before implementation to avoid shipping noisy rules.
- Should `--bug-hunt` findings appear in the score model? Currently CrossHair counterexamples are `severity=warning`; they could be promoted to `severity=error` in bug-hunt mode. Defer to implementation task.
