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
