# TDD Evidence: review-run dogfood follow-up

## Failing First

- `2026-03-16`: `hatch run specfact code review run --json packages/specfact-code-review/src/specfact_code_review/run/commands.py`
  returned a blocking `TEST_FAILURE` finding during repo dogfooding even though
  `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py -q`
  passed. Root cause: the TDD gate invoked `pytest --cov ...` without
  overriding the repo-wide `fail-under=80`, so targeted source-file runs failed
  on aggregate package coverage instead of test failures.
- `2026-03-16`: live runtime help still reported `--json` as stdout-oriented,
  and `hatch run specfact code review run --json --out /tmp/report.json ...`
  failed with `No such option: --out` before the command contract was updated.
- `2026-03-16`: local runtime validation required manual shadow-root copying and
  manifest rewriting before a dev module could be exercised through workspace
  `.specfact/modules`, which made the dogfooding workflow too brittle for
  repeatable development use.

## Passing

- `2026-03-16`: `hatch run pytest tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/run/test_runner.py -q`
  passed with `15 passed`.
- `2026-03-16`: `hatch run pytest tests/e2e/specfact_code_review/test_review_run_e2e.py -q`
  passed with `2 passed`.
- `2026-03-16`: `hatch run pytest tests/unit/test_link_dev_module_script.py -q`
  passed with `3 passed`.
- `2026-03-16`: project-scope runtime validation passed after copying the branch
  bundle into `.specfact/modules/specfact-code-review`, rewriting that shadow
  manifest in checksum-only mode with
  `python scripts/sign-modules.py --allow-unsigned --allow-same-version --payload-from-filesystem .specfact/modules/specfact-code-review/module-package.yaml`,
  and running the live CLI with `SPECFACT_ALLOW_UNSIGNED=1`:
  - `hatch run specfact code review run --help` showed `--json` writing to a file and exposed `--out`
  - `hatch run specfact code review run --json --out /tmp/review-report-*.json packages/specfact-code-review/src/specfact_code_review/run/commands.py`
    exited `0` and wrote a valid `ReviewReport` JSON file with `overall_verdict=PASS`
- `2026-03-16`: temporary-workspace runtime validation passed with the new local
  helper:
  - `/home/dom/git/nold-ai/specfact-cli-modules/.venv/bin/python scripts/link-dev-module.py specfact-code-review --source-dir /home/dom/git/nold-ai/specfact-cli-modules/packages/specfact-code-review --shadow-root /tmp/specfact-runtime-*/.specfact/modules`
    created a shadow module with symlinked live content and a manifest copy
    without `integrity`
  - `cd /tmp/specfact-runtime-* && SPECFACT_ALLOW_UNSIGNED=1 /home/dom/.local/bin/specfact code review run --help`
    loaded the project-scope shadow module and showed the updated `--json`/`--out` help
- `2026-03-16`: second-layer dogfooding improvements passed:
  - `hatch run pytest tests/unit/specfact_code_review/review/test_commands.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/ledger/test_client.py tests/unit/specfact_code_review/ledger/test_commands.py tests/unit/specfact_code_review/rules/test_updater.py tests/unit/specfact_code_review/tools/test_contract_runner.py tests/e2e/specfact_code_review/test_review_run_e2e.py -q`
    passed with `76 passed`
  - `printf 'n\n' | SPECFACT_ALLOW_UNSIGNED=1 hatch run specfact code review run --interactive --json --out /tmp/specfact-interactive-review.json`
    prompted for test inclusion and completed with `overall_verdict=PASS`, `score=115`, and `findings=[]`
  - `SPECFACT_ALLOW_UNSIGNED=1 hatch run specfact code review run --json --out /tmp/specfact-progress-check.json tests/fixtures/review/clean_module.py`
    printed per-step progress (`Running Ruff checks...`, `Running Radon complexity checks...`, etc.) and still ended with the JSON output path on stdout-compatible output
- `2026-03-16`: untracked-file discovery regression coverage added:
  - `tests/unit/specfact_code_review/run/test_commands.py::test_changed_files_from_git_diff_includes_untracked_python_files`
    verifies auto-detected review scope now includes both tracked and untracked Python files
  - `printf 'n\n' | SPECFACT_ALLOW_UNSIGNED=1 hatch run specfact code review run --interactive --json --out /tmp/specfact-untracked-review.json`
    no longer returned a false clean pass; it detected untracked files in scope and failed with findings against
    `scripts/link_dev_module.py` and `packages/specfact-code-review/src/specfact_code_review/_review_utils.py`
  - `SPECFACT_ALLOW_UNSIGNED=1 hatch run specfact code review run --json --out /tmp/specfact-third-pass-after.json`
    passed with `overall_verdict=PASS`, `score=115`, and `findings=[]` after the newly exposed script/test debt was fixed
  - `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run type-check`
    passed with `0 errors, 0 warnings, 0 notes`
  - `HATCH_DATA_DIR=/tmp/hatch-data HATCH_CACHE_DIR=/tmp/hatch-cache VIRTUALENV_OVERRIDE_APP_DATA=/tmp/virtualenv-appdata hatch run format`
    passed after reformatting the touched files

## Additional Failing Evidence

- `2026-03-16`: skill-driven self-review of the dogfooding follow-up initially
  produced a noisy `FAIL` report (`82 findings`, `24 blocking`) when test files
  from `git diff HEAD` were included by default and low-signal findings were not
  suppressible.
- `2026-03-16`: after adding the first round of second-layer fixes, interactive
  self-review excluding tests improved to `PASS_WITH_ADVISORY` but still
  reported source-level follow-up work:
  - `printf 'n\n' | SPECFACT_ALLOW_UNSIGNED=1 hatch run specfact code review run --interactive --json --out /tmp/specfact-interactive-review.json`
    returned `18 findings`, later reduced to `7 findings`, before the final
    cleanup batch removed the remaining advisories.
