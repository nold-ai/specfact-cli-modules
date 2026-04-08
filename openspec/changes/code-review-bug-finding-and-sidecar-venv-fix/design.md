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

**Non-Goals:**
- Replacing CrossHair with a different symbolic execution engine
- Adding semgrep cloud/registry rules (offline-first; rules must be bundled locally)
- Changing the score model or CI exit codes for bug-hunt findings
- Fixing CrossHair's analysis depth beyond timeout tuning

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

## Risks / Trade-offs

- **CrossHair false positives in bug-hunt mode**: Longer timeouts mean CrossHair explores more paths and may surface `SideEffectDetected` warnings on I/O-heavy functions. Mitigated: `_IGNORED_CROSSHAIR_PREFIXES` already filters `SideEffectDetected`; no change needed.
- **`bugs.yaml` rule maintenance**: Bundled semgrep rules can go stale. Mitigated: keep the initial set small (5–10 high-confidence rules), document in the file header that additions require a PR with test evidence.
- **MISSING_ICONTRACT auto-suppression masking real gaps**: If a bundle file imports icontract but only for one function, all other uncovered functions are still flagged. The auto-suppression only fires when zero icontract imports exist — so internal bundles are unaffected.
- **Sidecar exclusion breaking legitimate `.specfact/` source scanning**: No known repo puts application source under `.specfact/`. Risk is negligible.

## Migration Plan

No migrations required. Both changes are additive (`--bug-hunt` flag, `bugs.yaml` config) or bug fixes (venv exclusion, MISSING_ICONTRACT suppression). Existing behaviour is unchanged when `--bug-hunt` is not passed and when `bugs.yaml` is absent.

Patch version bump on `specfact-codebase` (sidecar bug fix). No version bump required on `specfact-code-review` for the `--bug-hunt` flag or MISSING_ICONTRACT change — both are backwards-compatible additions. If the semgrep `bugs.yaml` is shipped as a bundled resource, a minor bump on `specfact-code-review` is appropriate.

## Open Questions

- Which specific semgrep rules to include in `bugs.yaml` v1? Candidates: `python.lang.security.audit.dangerous-system-call`, `python.lang.correctness.useless-eqeq`, `python.lang.security.audit.hardcoded-password`, `python.lang.correctness.none-not-null`. Needs sign-off before implementation to avoid shipping noisy rules.
- Should `--bug-hunt` findings appear in the score model? Currently CrossHair counterexamples are `severity=warning`; they could be promoted to `severity=error` in bug-hunt mode. Defer to implementation task.
