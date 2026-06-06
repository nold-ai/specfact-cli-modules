# Why

Issue #255 reports that `specfact plan` is not accessible even when `nold-ai/specfact-project` is installed. The project bundle manifest only declares `project` in `commands`, so runtime command registry never loads the plan delegate.

# What Changes

- Add `plan` to `packages/specfact-project/module-package.yaml` commands list.
- Preserve required manifest metadata (`bundle_group_command`) so repo validation remains green.
- Update docs that describe project bundle exposed command groups to include plan.
- Add regression coverage for manifest command declaration.

# Impact

- Affected spec: project-command-surface
- Affected code: packages/specfact-project/module-package.yaml, docs/guides/marketplace.md, docs/reference/module-categories.md, tests
- Tracking: https://github.com/nold-ai/specfact-cli-modules/issues/255
