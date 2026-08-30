## Why

The modules repository tells development agents to uninstall user-scoped modules when a project-local copy shadows them. Review and bootstrap workflows repeatedly follow that instruction and remove `specfact-codebase` and `specfact-code-review` from the user scope, even though project-over-user precedence is expected and the user installation is still needed in other repositories.

## What Changes

- Replace destructive shadow-cleanup guidance in the development bootstrap and repository rules with an explicit preservation contract.
- Explain that project scope takes precedence only inside the current repository and does not delete or invalidate the user-scoped installation.
- Add regression coverage that fails if routine bootstrap guidance recommends `specfact module uninstall ... --scope user` again.
- Clarify the local test bootstrap name so in-memory import eviction cannot be mistaken for filesystem module removal.

## Capabilities

### Modified Capabilities

- `agent-governance-loading`: Repository bootstrap guidance preserves valid user-scoped module installations when project-local sources shadow them.

## Impact

- Affected code and guidance: `src/specfact_cli_modules/dev_bootstrap.py`, `docs/agent-rules/20-repository-context.md`, and focused unit tests.
- Paired core behavior: `nold-ai/specfact-cli#699` removes the same destructive recommendation from discovery and doctor diagnostics.
- Registry and signed module payload impact: none. No `registry/index.json`, `packages/*/module-package.yaml`, or signed module asset changes are planned.
- Published docs impact: none; the affected rule is contributor/agent guidance rather than a modules.specfact.io page.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Parent Epic**: [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162)
- **Bug Issue**: [#452](https://github.com/nold-ai/specfact-cli-modules/issues/452)
- **Paired Core Bug**: [nold-ai/specfact-cli#699](https://github.com/nold-ai/specfact-cli/issues/699)
- **Issue Relationships**: `#452` is a sub-issue of Epic `#162`; the paired core bug is a sub-issue of Feature `nold-ai/specfact-cli#353`.
- **Blocked By**: none
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: issue type, labels, assignee, parent, project assignment, In Progress status, and blocker metadata verified on 2026-08-29
- **Sanitized**: false
