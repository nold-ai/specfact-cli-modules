## Why

External repo validation (crewAI, gpt-researcher, and 8 OSS baseline repos) revealed two concrete tool gaps: the code review module produces no bug-finding signal on repos that don't use icontract, and the sidecar route extractor inflates route counts by scanning its own installed venv. Both blockers limit the tool's usefulness on arbitrary Python codebases.

## What Changes

- **Semgrep bug-finding rules**: Add a `bugs.yaml` semgrep config alongside the existing `clean_code.yaml`, covering Python security patterns, unsafe access, known bug-prone patterns. Wire it as a second semgrep pass in the runner.
- **CrossHair timeout increase + bug-hunt mode**: Expose a `--bug-hunt` flag on `specfact code review run` that raises `--per_path_timeout` from 2s to 10s and total timeout from 30s to 120s, giving CrossHair enough budget to find counterexamples in type-annotated code without icontract.
- **MISSING_ICONTRACT suppression on external repos**: When a reviewed codebase has zero icontract usage, suppress `MISSING_ICONTRACT` warnings rather than emitting one per public function. Auto-detect by scanning the reviewed files for any `@require`/`@ensure` import; if none found, omit the rule entirely for that run.
- **Sidecar venv self-scan fix**: Exclude `.specfact/` from the route extraction scan path in all framework extractors (`FlaskExtractor`, `FastAPIExtractor`, `DjangoExtractor`). Currently the sidecar installs deps into `.specfact/venv` then scans the full repo tree, picking up the installed framework's own source (gpt-researcher: 25,947 reported routes vs 19 real).

## Capabilities

### New Capabilities

- `code-review-bug-finding`: Semgrep security/bug rules pass and CrossHair bug-hunt mode — a second analysis layer focused on detecting actual bugs rather than clean-code style issues.

### Modified Capabilities

- `contract-runner`: CrossHair timeout parameters increase for bug-hunt mode; MISSING_ICONTRACT auto-suppressed when no icontract usage is detected in the reviewed files.
- `clean-code-policy-pack`: Second semgrep config (`bugs.yaml`) added alongside `clean_code.yaml`; semgrep runner gains a second config load pass.
- `review-run-command`: New `--bug-hunt` flag wired through `ReviewRunRequest` and `run_command`.

## Impact

- `packages/specfact-code-review/src/specfact_code_review/tools/contract_runner.py` — CrossHair timeout params, MISSING_ICONTRACT suppression logic
- `packages/specfact-code-review/src/specfact_code_review/tools/semgrep_runner.py` — second config pass for `bugs.yaml`
- `packages/specfact-code-review/src/specfact_code_review/run/commands.py` — `--bug-hunt` flag, `ReviewRunRequest` field
- `packages/specfact-code-review/src/specfact_code_review/run/runner.py` — pass `bug_hunt` flag through to tool steps
- `packages/specfact-code-review/.semgrep/bugs.yaml` — new file
- `packages/specfact-codebase/` — sidecar framework extractors: exclude `.specfact/` from scan paths
- No registry, manifest, or semver impact for specfact-code-review (behaviour change only; patch bump on specfact-codebase for the bug fix)
