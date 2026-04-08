## 1. Sidecar venv self-scan fix (specfact-codebase)

- [ ] 1.1 Add `_EXCLUDED_DIR_NAMES` constant and `_iter_python_files(root)` generator to `BaseFrameworkExtractor` in `frameworks/base.py` that skips `.specfact`, `.git`, `__pycache__`, `node_modules`
- [ ] 1.2 Replace `search_path.rglob("*.py")` with `self._iter_python_files(search_path)` in `FastAPIExtractor.detect()` and `FastAPIExtractor.extract_routes()`
- [ ] 1.3 Replace `rglob("*.py")` with `self._iter_python_files(...)` in `FlaskExtractor`
- [ ] 1.4 Replace `rglob("*.py")` with `self._iter_python_files(...)` in `DjangoExtractor` and `DRFExtractor`
- [ ] 1.5 Write tests: repo fixture with `.specfact/venv/` containing fake routes; assert extractor returns 0 routes from venv; assert real routes still found
- [ ] 1.6 Bump `specfact-codebase` patch version in `module-package.yaml`

## 2. MISSING_ICONTRACT auto-suppression (specfact-code-review)

- [ ] 2.1 Add `_has_icontract_usage(files: list[Path]) -> bool` to `contract_runner.py` — scan file ASTs for `from icontract import` or `import icontract`
- [ ] 2.2 In `run_contract_check`, call `_has_icontract_usage`; when `False`, skip `_scan_file` loop and return only CrossHair findings
- [ ] 2.3 Write tests: files with no icontract import → no `MISSING_ICONTRACT` findings; files with icontract import → findings emitted as before

## 3. CrossHair bug-hunt mode (specfact-code-review)

- [ ] 3.1 Add `bug_hunt: bool = False` parameter to `run_contract_check` and `_run_crosshair`; when `True` use `--per_path_timeout 10` and subprocess timeout 120s
- [ ] 3.2 Thread `bug_hunt` through `run_review` in `runner.py`
- [ ] 3.3 Add `bug_hunt: bool = False` field to `ReviewRunRequest` in `commands.py`
- [ ] 3.4 Add `--bug-hunt` Typer option to the `run` command; wire into `ReviewRunRequest`
- [ ] 3.5 Write tests: `ReviewRunRequest(bug_hunt=True)` propagates to CrossHair invocation with extended timeouts; default is unchanged

## 4. Semgrep bugs.yaml pass (specfact-code-review)

- [ ] 4.1 Create `packages/specfact-code-review/.semgrep/bugs.yaml` with an initial set of Python bug/security rules (≤10 high-confidence rules: dangerous system calls, useless equality checks, hardcoded passwords, swallowed broad exceptions with re-raise, unsafe `eval`/`exec`)
- [ ] 4.2 Add `find_semgrep_bugs_config()` to `semgrep_runner.py` — mirrors `find_semgrep_config` but returns `None` instead of raising when absent
- [ ] 4.3 Add `run_semgrep_bugs(files, *, bundle_root)` that calls `find_semgrep_bugs_config` and skips gracefully when `None`; map findings to `category="security"` or `category="correctness"`
- [ ] 4.4 Add `run_semgrep_bugs` to the `_tool_steps()` list in `runner.py` after the existing semgrep step
- [ ] 4.5 Write tests: file matching a `bugs.yaml` rule returns a finding; missing `bugs.yaml` returns no findings and no exception

## 5. TDD evidence and quality gates

- [ ] 5.1 Run `hatch run test` — all new and existing tests pass
- [ ] 5.2 Run `hatch run format && hatch run type-check && hatch run lint` — clean
- [ ] 5.3 Run `specfact code review run --json --out .specfact/code-review.json` — resolve any findings
- [ ] 5.4 Record passing test output in `TDD_EVIDENCE.md`
