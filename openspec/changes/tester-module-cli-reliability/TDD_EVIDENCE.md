# TDD Evidence: tester-module-cli-reliability

## Readiness

- Worktree: `/home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/tester-command-reliability`
- Branch: `feature/tester-command-reliability`
- Modules feature: nold-ai/specfact-cli-modules#305
- Modules story: nold-ai/specfact-cli-modules#306
- Paired core story: nold-ai/specfact-cli#594

## Source Ownership

- `nold-ai/specfact-cli#586`: module-owned `specfact project regenerate` runtime hardening.
- `nold-ai/specfact-cli#587`: split; modules owns canonical `specfact project sync bridge` help/docs/prompts.
- `nold-ai/specfact-cli#588`: split; modules owns `specfact code import` command contract/help.
- `nold-ai/specfact-cli#590`: split; modules owns codebase/code-review semgrep diagnostic adoption.
- `nold-ai/specfact-cli#591`: module-owned backlog auth missing-subcommand UX.
- `nold-ai/specfact-cli#592`: module-owned backlog delta status config/default contract.

## Failing Before

- Targeted module regression suite run from the paired core Hatch environment with module packages on `PYTHONPATH` -> 6 failed before production edits.
  - `backlog auth` without a subcommand only emitted Click's generic missing-command error and did not print available auth subcommands.
  - `backlog delta status github` required `--project-id` and did not resolve documented provider config or repo owner/name flags.
  - `project sync bridge --help` did not expose the canonical `specfact project sync bridge` path expected by docs/tests.
  - `code import service-a --repo .` did not provide migration guidance to supported canonical ordering.
  - Prompt command validation still modeled removed flat shims such as `specfact sync`, `specfact plan`, `specfact import`, and `specfact migrate`.
- `PYTHONPATH=<module-srcs>:<core-src> hatch run pytest tests/unit/test_global_cli_error_contract.py -q` after adding global module-context tests -> 2 failed before the shared core renderer was imported for direct module apps.
  - Direct module groups did not consistently emit help plus missing-subcommand guidance.
  - Direct module command contexts did not inherit the shared missing-parameter renderer.

## OpenSpec Validation

- `openspec validate tester-module-cli-reliability --strict` -> passed.

## Passing After

- `PYTHONPATH=<module-srcs>:<core-src> hatch run python scripts/generate-command-overview.py --check` -> passed.
- `hatch run check-command-contract` -> passed: `check-command-contract: OK (86 generated module command path(s) validated)`.
- `PYTHONPATH=<module-srcs>:<core-src> hatch run python scripts/check-docs-commands.py` -> passed: `Docs command validation passed with no findings.`
- `PYTHONPATH=<module-srcs>:<core-src> hatch run python scripts/check-prompt-commands.py` -> passed: `Prompt command validation passed with no findings.`
- `PYTHONPATH=<module-srcs>:<core-src> hatch run pytest tests/unit/test_global_cli_error_contract.py tests/unit/specfact_backlog/test_auth_commands.py tests/unit/specfact_backlog/test_delta_command_contract.py tests/e2e/specfact_project/test_help_smoke.py::test_project_sync_bridge_help_uses_canonical_command_path tests/unit/specfact_codebase/test_import_command_contract.py tests/unit/test_check_prompt_commands_script.py::test_module_app_mounts_do_not_include_removed_flat_shims -q` -> 11 passed.
- Paired core Hatch environment with modules packages on `PYTHONPATH`: `hatch run pytest /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/tester-command-reliability/tests/unit/test_global_cli_error_contract.py -q` -> 2 passed.
- `hatch run pytest tests/unit/specfact_codebase/test_import_command_contract.py tests/unit/test_global_cli_error_contract.py -q` -> 3 passed.
- `hatch run pytest tests/unit/specfact_project/test_regenerate_command_contract.py -q` -> 1 failed before the `project regenerate` null-graph guard because the command still raised a raw `NoneType` attribute error.
- `hatch run pytest tests/e2e/specfact_project/test_help_smoke.py::test_project_sync_bridge_help_uses_canonical_command_path tests/unit/specfact_project/test_regenerate_command_contract.py -q` -> 2 passed after the typed `project regenerate` diagnostic and canonical sync-bridge help checks.
- `hatch run pytest tests/unit/test_check_prompt_commands_script.py::test_iter_prompt_paths_includes_resource_templates tests/unit/test_check_prompt_commands_script.py::test_validate_prompt_commands_reports_stale_command_in_resource_template tests/unit/test_check_prompt_commands_script.py::test_docs_review_workflow_runs_prompt_command_validation tests/unit/test_check_prompt_commands_script.py::test_pre_commit_prompt_validation_covers_cli_command_implementations -q` -> 4 passed after extending prompt command validation to module resource templates, YAML/Jinja2/text/JSON assets, pre-commit, and docs-review path filters.
- Release hygiene:
  - Changed module package manifests were patch-bumped: `specfact-backlog` `0.41.26`, `specfact-codebase` `0.41.11`, `specfact-govern` `0.40.22`, `specfact-project` `0.41.19`, and `specfact-spec` `0.40.19`.
  - `hatch run python scripts/sign-modules.py --allow-unsigned --payload-from-filesystem packages/specfact-backlog/module-package.yaml packages/specfact-codebase/module-package.yaml packages/specfact-govern/module-package.yaml packages/specfact-project/module-package.yaml packages/specfact-spec/module-package.yaml` -> passed, refreshing payload checksums. No signing key variables were configured in this shell, so this was checksum-only local signing.
  - `hatch run python scripts/verify-modules-signature.py --payload-from-filesystem --enforce-version-bump --version-check-base origin/dev` -> passed.
  - `hatch run generate-command-overview` -> passed after the manifest version bumps.
  - `hatch run check-command-overview` -> passed after regeneration.
  - `hatch run python scripts/check-docs-commands.py` -> passed after regeneration.
- `specfact code import from-code --help` and `specfact code import from-bridge --help` now render explicit subcommand usage instead of parent `code import` usage; `from-code` is visible in the generated command overview and `llms.txt`.
- `scripts/pre-commit-quality-checks.sh` regenerates and stages module `llms.txt`, `docs/reference/commands.generated.json`, and `docs/reference/commands.generated.md`, then validates overview freshness and source-backed command behavior before docs/prompt command validation.
- PR validation now checks module command overview freshness, generated command contract behavior, docs/prompt command references, and delegates the package-manager runtime smoke to the paired core workflow checkout.
- `openspec validate tester-module-cli-reliability --strict` -> passed after the focused global contract rerun.
- CI duplicate full-suite hardening:
  - Modules PR orchestrator now has one full-suite owner: `hatch run test`.
  - Contract validation now runs `hatch run contract-test-contracts`; smart-test validation now runs configuration-only `hatch run smart-test-check`.
  - The broad `contract-test` alias now maps to scoped contract checks, not the full smart-test runner.
  - Pre-commit fallback and the PR template now point to `hatch run contract-test-contracts`, `hatch run smart-test-check`, and `hatch run test` instead of encouraging three broad test invocations.
  - `hatch run pytest tests/unit/workflows/test_pr_orchestrator_signing.py tests/unit/tools/test_contract_first_smart_test.py -q` -> 10 passed.
  - `hatch run pytest tests/unit/workflows/test_pr_orchestrator_signing.py -q` -> 6 passed after the PR template/pre-commit wording updates.
  - `hatch run contract-test -q` -> 28 passed, 785 deselected, 2 warnings, confirming the legacy alias is now scoped contract validation.
- Quality gates after CI duplicate hardening:
  - `hatch run format` -> passed.
  - `hatch run type-check` -> passed.
  - `hatch run lint` -> passed.
  - `hatch run yaml-lint` -> passed.
  - `openspec validate tester-module-cli-reliability --strict` -> passed.
- SpecFact code review bug-hunt:
  - Initial `specfact code review run --scope changed --bug-hunt --include-tests --json --out .specfact/code-review.changed.json` found actionable slice blockers in `backlog_core/commands/delta.py`, `specfact_codebase/repro/commands.py`, and `scripts/check-command-contract.py`.
  - Fixed the actionable blockers by adding an explicit typed guard after missing delta context exits, replacing unused TOML fallback imports with `importlib.util.find_spec`, and casting the generated Typer app before runner invocation.
  - Rerun with paired module source wired through `SPECFACT_MODULES_ROOTS`/`PYTHONPATH` -> `Review completed with 396 findings (161 blocking)`.
  - Remaining blockers are legacy changed-file-scope findings in large pre-existing module command implementations: 56 `clean_code` complexity findings, 92 `kiss` size/nesting/parameter findings, 12 private unused-function findings, and 1 pylint timeout `tool_error`. They are not introduced by the command reliability edits, but the review tool reports them because those files contain updated command help text and are therefore in changed scope.

## Deferred / Not Covered In This Slice

- Full `smart-test` was not rerun after narrowing the PR workflow, because the targeted workflow regression suite and scoped `contract-test` now verify the duplicate full-suite behavior directly.
- Refactoring the 161 remaining legacy modules code-review blockers requires a separate broad cleanup change across `specfact-project`, `specfact-codebase`, `specfact-govern`, and `specfact-spec`; doing that inside the tester command reliability patch would change unrelated command internals with high regression risk.

## Follow-up Review Fixes

- Addressed follow-up CI/review findings:
  - Docs review and PR orchestrator workflows now resolve a matching paired `specfact-cli` branch when present, falling back to the PR base branch (`main` or `dev`) and then `dev`.
  - Touched checkout steps set `persist-credentials: false`.
  - Runtime discovery smoke in modules CI now runs via `hatch run python specfact-cli/scripts/runtime_discovery_smoke.py` so the paired core script can import its dependencies.
  - Generated command overview no longer marks callback-only help/error groups such as `specfact backlog auth` as executable, while preserving executable callback groups such as `specfact code import` and `specfact code repro`.
  - Prompt command validation now indexes nested Typer groups and Typer option metadata by attribute, matching the generated command overview behavior.
  - Pre-commit refuses to auto-stage generated command artifacts when command overview inputs have unstaged changes.
  - `tasks.md` quality/review checklist now matches the recorded evidence and documented review exception.
- Follow-up verification:
  - `hatch run pytest tests/unit/test_check_prompt_commands_script.py tests/unit/workflows/test_pr_orchestrator_signing.py tests/unit/test_check_docs_commands_script.py tests/unit/test_pre_commit_quality_parity.py -q` -> 39 passed.
  - `hatch run yaml-lint && hatch run check-command-overview && hatch run check-command-contract && hatch run python scripts/check-docs-commands.py && hatch run python scripts/check-prompt-commands.py && openspec validate tester-module-cli-reliability --strict` -> passed.
  - `hatch run python /home/dom/git/nold-ai/specfact-cli-worktrees/feature/tester-command-reliability/scripts/runtime_discovery_smoke.py --modules-repo /home/dom/git/nold-ai/specfact-cli-modules-worktrees/feature/tester-command-reliability --launcher pipx --launcher uv-run --launcher uvx` -> passed for all three remaining package-manager launchers.
  - `hatch run format` -> passed.
  - `hatch run lint` -> failed on an existing unrelated type mismatch in `tests/unit/specfact_backlog/conftest.py` (`typer.testing.Result` vs `click.testing.Result`); none of the follow-up edits touched that file. Focused touched-scope tests and validators above pass.

## Follow-up PR Thread Fixes

- Validated live PR #307 review threads and CI annotations after the previous follow-up.
- Addressed remaining actionable findings:
  - Paired core checkout steps in touched workflows now pin `actions/checkout` to `34e114876b0b11c390a56381ad16ebd13914f8d5` while retaining `persist-credentials: false`.
  - `backlog delta status` falls back to missing-context guidance when `.specfact/backlog-config.yaml` is malformed YAML instead of leaking parser errors.
  - `project snapshot` now uses the same typed backlog-graph guard as `project regenerate`.
  - Semgrep plugin status preserves the active environment probe message returned by core `check_tool_in_env`.
  - Generated command JSON loading in `scripts/check-docs-commands.py` fails fast on malformed JSON or malformed entries.
  - Project, govern, and spec prompt guidance no longer uses `specfact project --help` as an executable workflow placeholder; examples now use concrete generated-contract commands such as `code import from-code`, `project health-check`, `project export`, and `govern enforce sdd`.
  - Project overview docs were reduced to command families present in the generated project command contract.
  - OpenSpec source tracking now includes source bug `#589`.
- Follow-up verification:
  - `hatch run pytest tests/unit/specfact_backlog/test_delta_command_contract.py tests/unit/specfact_project/test_regenerate_command_contract.py tests/unit/specfact_project/test_code_analyzer_semgrep_status.py tests/unit/test_check_docs_commands_script.py tests/unit/test_check_prompt_commands_script.py tests/unit/workflows/test_pr_orchestrator_signing.py tests/unit/test_pre_commit_quality_parity.py -q` -> 47 passed.
  - `hatch run yaml-lint && hatch run check-command-overview && hatch run check-command-contract && hatch run python scripts/check-docs-commands.py && hatch run python scripts/check-prompt-commands.py && openspec validate tester-module-cli-reliability --strict` -> passed.
  - `hatch run format` -> passed.

## Follow-up Code Review Enforcement Modes

- Added explicit code-review enforcement policies:
  - `full`: strict mode; any blocking finding in reviewed files blocks the run.
  - `changed`: default CLI/pre-commit mode; blocking findings only block when they target changed lines, while legacy blockers remain in JSON evidence.
  - `shadow`: evidence-only mode; findings are reported but the run does not block.
- Runtime and gate wiring:
  - `specfact code review run --enforcement full|changed|shadow` is now the primary runtime option.
  - Deprecated `--mode enforce|shadow` remains supported as a compatibility alias (`enforce` maps to `full`).
  - Pre-commit/CI wrapper reads `SPECFACT_CODE_REVIEW_ENFORCEMENT`, defaults to `changed`, and uses cached staged diffs for changed-line evidence.
  - Checked the shipped GitHub workflow Jinja template; it does not invoke code review, so no PR review template change was required.
- Follow-up verification:
  - `hatch run pytest tests/unit/scripts/test_pre_commit_code_review.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/review/test_commands.py tests/unit/docs/test_code_review_docs_parity.py tests/unit/test_pre_commit_quality_parity.py -q` -> included in the final combined 172-test focused suite.
  - `hatch run pytest tests/unit/specfact_backlog/test_delta_command_contract.py tests/unit/specfact_project/test_regenerate_command_contract.py tests/unit/specfact_project/test_code_analyzer_semgrep_status.py tests/unit/test_check_docs_commands_script.py tests/unit/test_check_prompt_commands_script.py tests/unit/workflows/test_pr_orchestrator_signing.py tests/unit/test_pre_commit_quality_parity.py tests/unit/scripts/test_pre_commit_code_review.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/run/test_commands.py tests/unit/specfact_code_review/review/test_commands.py tests/unit/docs/test_code_review_docs_parity.py -q` -> 172 passed.
  - `hatch run generate-command-overview` -> passed.
  - `hatch run check-command-overview` -> passed.
  - `hatch run check-command-contract` -> passed: `check-command-contract: OK (86 generated module command path(s) validated)`.
  - `hatch run python scripts/check-docs-commands.py` -> passed.
  - `hatch run python scripts/check-prompt-commands.py` -> passed.
  - `hatch run lint` -> passed.
  - Documentation follow-up after user review:
    - Updated broader user-facing docs, tutorials, guides, bundled skills, and `/specfact.08-simplify` prompt examples to show `--enforcement full|changed|shadow`.
    - `hatch run python scripts/check-docs-commands.py` -> passed.
    - `hatch run python scripts/check-prompt-commands.py` -> passed.
    - `hatch run pytest tests/unit/docs/test_code_review_docs_parity.py tests/unit/test_guided_simplify_resources.py tests/unit/specfact_code_review/rules/test_updater.py tests/unit/test_check_prompt_commands_script.py -q` -> 41 passed.

## Second Follow-up PR CI Fixes

- Re-checked paired core PR #595 after pushing modules. Fresh core CLI validation failed while importing paired modules: `specfact_backlog/backlog_core/commands/delta.py` imported `typer._click.core`, which is not available under the core CI Typer dependency range.
- Fixed the backlog delta status callback to use public `typer.Context` instead of Typer's private vendored Click namespace.
- Added `test_delta_command_avoids_private_typer_click_import`.
- Follow-up verification:
  - `hatch run pytest tests/unit/specfact_backlog/test_delta_command_contract.py -q` -> 4 passed.
  - `rg -n "from typer\\._click|TyperClickContext" packages scripts docs` -> no matches.
  - `hatch run check-command-overview` -> passed.
  - `hatch run check-command-contract` -> passed: `check-command-contract: OK (86 generated module command path(s) validated)`.
  - `hatch run lint` -> passed.
  - `openspec validate tester-module-cli-reliability --strict` -> passed.

## Third Follow-up PR Review Fixes

- Re-checked live PR #307 review threads after the enforcement-mode documentation updates.
- Addressed still-valid findings:
  - Changed enforcement now skips unreadable or non-UTF-8 untracked files instead of crashing when collecting changed-line evidence.
  - Prompt command validation and command overview generation no longer assume every Click parameter with `opts` also exposes `secondary_opts`.
  - Typer app conversion sites in prompt validation and command overview generation now cast the generated Click command explicitly, resolving follow-up type-safety review errors.
  - Pre-commit changed-line parsing only treats `+++ ` as a destination-file header when it follows a `--- ` source header, so staged content lines beginning with `++ ` cannot corrupt the changed-line map.
  - `/specfact.04-sdd` and `/specfact.07-contracts` prompt parameter docs now describe active-plan fallback consistently.
  - `/specfact.04-sdd` no longer claims a distinct plan-update CLI command exists before SDD regeneration.
- Reviewed and intentionally kept the `changed` default for `specfact code review run --enforcement`: this is the requested default policy for legacy-noise-tolerant gates, while `full` remains available and documented for strict CI/pre-commit enforcement.
- Reviewed the remaining advisory code-review warnings after the final amend. Fixed the valid line-length warning. Left the generator script's `print()` and missing-contract warnings as documented exceptions: this existing CLI utility intentionally writes generated diffs/status to stdout, and adding icontract decorators to its existing script entry points is outside the review-thread fix scope.
- Follow-up verification:
  - `hatch run format` -> passed.
  - `hatch run pytest tests/unit/test_pre_commit_quality_parity.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/test_check_prompt_commands_script.py -q` -> 66 passed.
  - `hatch run pytest tests/unit/test_check_prompt_commands_script.py tests/unit/test_pre_commit_quality_parity.py -q` -> 26 passed after the final type-safety cleanup.
  - `hatch run python scripts/check-prompt-commands.py` -> passed.
  - `hatch run generate-command-overview` -> passed.
  - `hatch run check-command-overview` -> passed.
  - `hatch run check-command-contract` -> passed: `check-command-contract: OK (86 generated module command path(s) validated)`.
  - `hatch run python scripts/check-docs-commands.py` -> passed.
  - `hatch run lint` -> passed.
  - `openspec validate tester-module-cli-reliability --strict` -> passed.

## Fourth Follow-up PR Review Fixes

- Re-checked the seven PR #307 CodeRabbit findings against current code:
  - Kept `changed` as the default enforcement mode because it is the requested default policy, and added an explicit runtime notice that `--enforcement full` is required for strict CI gates.
  - Confirmed unreadable untracked files are skipped safely when collecting changed-line evidence.
  - Confirmed `/specfact.04-sdd` and `/specfact.07-contracts` active-plan/default prompt text is corrected.
  - Confirmed `_command_options` guards `secondary_opts`.
  - Confirmed staged diff parsing only recognizes `+++ ` headers after `--- ` source headers.
  - Confirmed the duplicate SDD command placeholder was removed instead of replaced with a nonexistent plan-update command.
- Addressed still-valid outside-diff findings:
  - Replaced `specfact project --help` placeholders in `/specfact.03-review` with the current bundled `/specfact.03-review --list-questions`, `--list-findings`, and `--answers` prompt command surface. Local runtime confirms `specfact plan` is not mounted and `specfact project` has no review subcommand in this module contract.
  - Added `specfact_govern.enforce.commands` and `specfact_spec.contract.commands` to docs command validation mounts, without reintroducing removed flat shims such as `specfact plan`.
- Validation:
  - `hatch run format` -> passed.
  - `hatch run generate-command-overview` -> passed.
  - `hatch run pytest tests/unit/specfact_code_review/review/test_commands.py tests/unit/test_check_docs_commands_script.py tests/unit/test_check_prompt_commands_script.py -q` -> 48 passed.
  - `hatch run check-command-overview` -> passed.
  - `hatch run check-command-contract` -> passed: `check-command-contract: OK (86 generated module command path(s) validated)`.
  - `hatch run python scripts/check-docs-commands.py` -> passed.
  - `hatch run python scripts/check-prompt-commands.py` -> passed.
  - `hatch run lint` -> passed.
  - `openspec validate tester-module-cli-reliability --strict` -> passed.

## Fifth Follow-up PR Review Fix

- Re-checked the PR #307 review finding about ambiguous `specfact code review run` enforcement flags against current code.
- Finding status: valid. `--mode shadow --enforcement changed` could bypass the existing `_resolve_cli_enforcement` conflict check because `changed` is also the default.
- Fix:
  - Added an early `_execute_review_run` guard that rejects deprecated `--mode` when Click reports `--enforcement` was explicitly supplied.
  - Preserved legacy `--mode` compatibility when `--enforcement` is only defaulted.
  - Added a regression test that confirms `run_command` is not called for the ambiguous flag combination.
  - Added a `specfact-code-review-run` CLI contract anti-pattern scenario for `--mode shadow --enforcement changed`.
  - Updated the existing blocking error-level report scenario to request `--enforcement full`, matching the intended `changed` default policy.
- Validation:
  - `hatch run pytest tests/unit/specfact_code_review/review/test_commands.py -q` -> 15 passed.
  - `hatch run validate-cli-contracts` -> passed: `Validated 3 CLI contract scenario files.`
  - `hatch run pytest tests/integration/specfact_code_review/test_cli_contract_review_run_reports.py -q` -> 3 passed.
  - `hatch run sign-modules --changed-only --bump-version patch --allow-unsigned --payload-from-filesystem` -> bumped `packages/specfact-code-review/module-package.yaml` from `0.47.40` to `0.47.41` and refreshed checksum.
  - `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump` -> passed: `Verified 6 module manifest(s).`
  - `hatch run pytest tests/unit/specfact_code_review/review/test_commands.py tests/integration/specfact_code_review/test_cli_contract_review_run_reports.py -q` -> 18 passed.
  - `hatch run lint` -> passed.
  - `hatch run python scripts/pre_commit_code_review.py packages/specfact-code-review/src/specfact_code_review/review/commands.py tests/unit/specfact_code_review/review/test_commands.py tests/cli-contracts/specfact-code-review-run.scenarios.yaml openspec/changes/tester-module-cli-reliability/TDD_EVIDENCE.md packages/specfact-code-review/module-package.yaml` -> passed with one info-only advisory on the pre-existing Typer `run` command length; left out of scope for this review-thread fix.
  - `openspec validate tester-module-cli-reliability --strict` -> passed.
