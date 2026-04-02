## Context

Official bundles ship `module-package.yaml` with `commands` and optional `bundle_dependencies`. The registry copies `bundle_dependencies` into `registry/index.json` during publish (`publish-modules.yml`). `nold-ai/specfact-codebase` already depends on `nold-ai/specfact-project`; `nold-ai/specfact-code-review` shares the `code` command group but lists no peer dependencies, so installs can omit the codebase bundle until users discover missing `code` subcommands manually.

## Goals / Non-Goals

**Goals:**

- Declare `bundle_dependencies` for code-review so manifest and registry advertise the need for the codebase bundle (and, transitively via codebase, project).
- Keep manifest and registry `bundle_dependencies` fields aligned after version bump and publish.
- Add automated checks or tests that prevent drift between YAML manifest and JSON registry for this metadata where practical.

**Non-Goals:**

- Changing SpecFact CLI resolver logic in this repo (core lives in `specfact-cli`); if transitive install behavior is incomplete there, track a sibling issue in core.
- Re-evaluating every bundle’s full dependency graph beyond the known code-review gap (optional follow-up audits).

## Decisions

1. **Dependency list for code-review** — Add a single entry `nold-ai/specfact-codebase`. Rationale: codebase already depends on project; duplicating project on code-review would be redundant unless CLI only installs direct deps. If CLI resolves transitive `bundle_dependencies`, one entry is sufficient. If not, extend to also list `nold-ai/specfact-project` after verifying core behavior.
2. **Semver** — Treat as **minor** if users perceive new auto-install behavior; **patch** if manifest/registry alignment only. Default to minor when `bundle_dependencies` changes user-facing install resolution.
3. **Verification** — Prefer extending existing registry/manifest tests or `verify-modules-signature` expectations over one-off scripts.

## Risks / Trade-offs

- **Circular dependency** — Code-review must not create a cycle. Codebase does not depend on code-review → safe.
- **Larger install footprint** — Users installing only code-review will pull more bundles; acceptable per goal of “full command group.”
- **Core vs modules** — If CLI ignores `bundle_dependencies`, this change still documents intent; follow-up in specfact-cli.

## Migration Plan

1. Implement on a feature branch from `dev`; bump `specfact-code-review` version; update manifest + registry.
2. Run publish/sign verification locally; publish via normal workflow.
3. No data migration for end users beyond reinstalling or updating modules.

## Open Questions

- Confirm in specfact-cli (or docs) that `bundle_dependencies` triggers transitive installs; if not, whether to add `nold-ai/specfact-project` explicitly to code-review.
