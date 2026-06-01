## Why

Primary tester reports filed in `nold-ai/specfact-cli#586` through `#592` expose module-owned CLI contract failures: project regeneration crashes on missing/null bundle data, sync bridge help still advertises removed flat commands, code import docs/help allow invalid option ordering, semgrep diagnostics miss the active uv environment, and backlog command groups report missing input without actionable help.

Modules owns the runnable command implementations, module docs, prompt resources, and module command overview artifacts. Core owns the shared CLI error contract and package-manager runtime matrix in paired change `tester-cli-reliability`.

## What Changes

- Harden project, codebase, sync, and backlog command contracts against the tester-reported failures.
- Apply the shared CLI error contract in module command groups: missing subcommands and missing parameters show help plus the missing information.
- Generate deterministic module command overview artifacts for AI agents and docs validation.
- Replace module docs/prompt/template command validation allowlists that still accept legacy flat shims.
- Align semgrep/tool diagnostics with the active uv/hatch/pip/pipx execution context exposed by core helpers.

## Capabilities

### New Capabilities

- `module-command-overview`
- `module-cli-error-contract`

### Modified Capabilities

- `modules-docs-command-validation`
- `backlog-delta`
- `code-review-tool-dependencies`

## Impact

- Affected packages: `specfact-project`, `specfact-codebase`, `specfact-backlog`, and command validation scripts.
- Affected docs/resources: module command docs, prompt resources, generated `llms.txt`, generated command reference Markdown/JSON, README links.
- Affected tests: project regenerate diagnostics, sync bridge help text, code import contract/migration error, semgrep active-env probing, backlog auth/delta status CLI behavior, generated command overview freshness.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Parent Feature**: [#305](https://github.com/nold-ai/specfact-cli-modules/issues/305), plus existing module features [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161), [#147](https://github.com/nold-ai/specfact-cli-modules/issues/147), and [#234](https://github.com/nold-ai/specfact-cli-modules/issues/234)
- **Change User Story**: [#306](https://github.com/nold-ai/specfact-cli-modules/issues/306)
- **Source Bugs**: [nold-ai/specfact-cli#586](https://github.com/nold-ai/specfact-cli/issues/586), [#587](https://github.com/nold-ai/specfact-cli/issues/587), [#588](https://github.com/nold-ai/specfact-cli/issues/588), [#589](https://github.com/nold-ai/specfact-cli/issues/589), [#590](https://github.com/nold-ai/specfact-cli/issues/590), [#591](https://github.com/nold-ai/specfact-cli/issues/591), [#592](https://github.com/nold-ai/specfact-cli/issues/592)
- **Paired Core Change**: `tester-cli-reliability`, tracked by [nold-ai/specfact-cli#594](https://github.com/nold-ai/specfact-cli/issues/594)
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: GitHub feature and story created; project/parent fields may need project-board field sync if CLI auth lacks project scope.
- **Sanitized**: false
