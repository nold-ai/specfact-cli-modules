# TDD Evidence — project-02-plan-root-command-fix

## Failing-before evidence
- `specfact plan --help` in a clean temp workspace without installed project module failed with:
  - `Module 'nold-ai/specfact-project' is not installed.`

## Implementation changes
- Added `plan` to `packages/specfact-project/module-package.yaml` `commands` list.
- Added regression test `tests/unit/test_specfact_project_manifest_commands.py`.

## Passing-after evidence
- `pytest -q tests/unit/test_specfact_project_manifest_commands.py` → **passed**.
- `./scripts/pre-commit-quality-checks.sh` → **passed** in this environment.

## Tooling verification
- OpenSpec npm install command verified from openspec.dev:
  - `npm install -g @fission-ai/openspec@latest`
- `openspec --version` returned `1.3.1` after install.


## Runtime validation with linked local module
- Cloned paired core repo to `/workspace/specfact-cli` and set `SPECFACT_CLI_REPO` so hatch bootstrap can resolve core dependency.
- Linked local module shadow: `hatch run python scripts/link_dev_module.py specfact-project --source-dir ... --shadow-root <tmp>/.specfact/modules`.
- Ran `SPECFACT_ALLOW_UNSIGNED=1 .../specfact module list` and confirmed `nold-ai/specfact-project 0.41.9` is enabled.
- Ran `SPECFACT_ALLOW_UNSIGNED=1 .../specfact plan --help` and confirmed root `plan` command renders usage and subcommands.
