# TDD Evidence — project-02-plan-root-command-fix

## Failing-before evidence

Regression reproduced with `nold-ai/specfact-project` installed but plan not delegated by registry.

Workspace verification (before manifest fix):

```bash
$ SPECFACT_ALLOW_UNSIGNED=1 /workspace/specfact-cli-modules/.venv/bin/specfact module list
...
│ nold-ai/specfact-project │ 0.41.8  │ enabled │ [official] │ nold-ai │
...

$ SPECFACT_ALLOW_UNSIGNED=1 /workspace/specfact-cli-modules/.venv/bin/specfact plan --help
Module 'nold-ai/specfact-project' is not installed.
The plan command group is provided by that module.
```

This proves the bundle is installed but root `plan` command was not delegated.

## Implementation changes

- Added `plan` to `packages/specfact-project/module-package.yaml` `commands` list.
- Restored required `bundle_group_command: project` manifest key for repo validators.
- Added regression test `tests/unit/test_specfact_project_manifest_commands.py`.

## Passing-after evidence

- `pytest -q tests/unit/test_specfact_project_manifest_commands.py` → **passed**.
- `./scripts/pre-commit-quality-checks.sh` → **passed** in this environment.
- `SPECFACT_ALLOW_UNSIGNED=1 .../specfact plan --help` now renders plan usage and subcommands.

## Tooling verification

- OpenSpec npm install command verified from openspec.dev:
  - `npm install -g @fission-ai/openspec@latest`
- `openspec --version` returned `1.3.1` after install.

## Runtime validation with linked local module

- Cloned paired core repo to `/workspace/specfact-cli` and set `SPECFACT_CLI_REPO` so hatch bootstrap can resolve core dependency.
- Linked local module shadow: `hatch run python scripts/link_dev_module.py specfact-project --source-dir ... --shadow-root <tmp>/.specfact/modules`.
- Ran `SPECFACT_ALLOW_UNSIGNED=1 .../specfact module list` and confirmed `nold-ai/specfact-project 0.41.9` is enabled.
- Ran `SPECFACT_ALLOW_UNSIGNED=1 .../specfact plan --help` and confirmed root `plan` command renders usage and subcommands.
