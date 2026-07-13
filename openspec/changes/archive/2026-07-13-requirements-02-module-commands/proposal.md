# Change: Requirements Runtime Commands

## Why

SpecFact needs a module-owned `requirements` command group that imports,
normalizes, validates, and inspects upstream requirement context for validation
evidence. It should not become the authoring stack for requirements, since
teams may already use Spec Kit, OpenSpec, Jira, GitHub Issues, Azure DevOps,
Linear, documents, or another planning source.

## Ownership Alignment (2026-06-06)

- Repository assignment: `split/rescope`
- Modules-owned scope retained here: grouped `specfact requirements ...`
  runtime commands, module manifest wiring, docs, and adapter-facing command
  behavior for normalized requirement inputs.
- Core-owned scope remains the shared requirements input model, adapter helper
  APIs, evidence contracts, and missing-module root diagnostics.
- Runtime commands MUST consume the paired core helpers from
  `nold-ai/specfact-cli#239`.
- Requirement authoring templates are no longer critical-path scope.

## What Changes

- **NEW**: `specfact requirements import` command for local requirement records
  and adapter-produced source-attributed records.
- **NEW**: `specfact requirements validate` command that delegates to the core
  profile-aware validation boundary.
- **NEW**: `specfact requirements list` and `specfact requirements coverage`
  commands for machine-readable coverage inspection.
- **NEW**: Requirements module manifest and command overview wiring.
- **NEW**: Command runtime preserves bounded core diagnostics instead of
  generating free-form planning prose.
- **REMOVED FROM CRITICAL PATH**: Interactive requirement authoring and full
  requirement lifecycle management.

## Capabilities

### New Capabilities

- `requirements-validation-runtime`: Module runtime commands for importing,
  normalizing, validating, and inspecting upstream requirement context.

### Modified Capabilities

- `module-io-contract`: Requirements implementation focuses on import,
  validation, and coverage hooks for evidence.
- `backlog-adapter`: Backlog adapters can provide source-attributed requirement
  snippets.

## Impact

- **Affected specs**: `requirements-module`, `module-io-contract`,
  `backlog-adapter`
- **Affected code**:
  - `packages/specfact-requirements/module-package.yaml`
  - `packages/specfact-requirements/src/specfact_requirements/requirements/commands.py`
  - `packages/specfact-requirements/src/specfact_requirements/requirements/runtime.py`
  - `scripts/generate-command-overview.py`
  - `scripts/check-bundle-imports.py`
  - `tests/conftest.py`
- **Affected tests**:
  - `tests/unit/specfact_requirements/test_requirements_runtime.py`
  - `tests/integration/specfact_requirements/test_command_apps.py`
- **Affected docs**:
  - `docs/bundles/requirements/overview.md`
  - `docs/reference/commands.generated.json`
  - `docs/reference/commands.generated.md`
  - `docs/_data/nav.yml`
  - `llms.txt`
- **Integration points**: Consumes the core helper APIs from
  `nold-ai/specfact-cli#239` and the `requirements.inputs` model from
  `requirements-01-data-model`.
- **Rollback plan**: remove the requirements bundle package, generated command
  overview rows, docs/nav entries, tests, and module manifest. Existing
  `requirements.inputs` bundle data remains compatible because the data model is
  core-owned.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #165
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/165>
- **Core Counterpart**: nold-ai/specfact-cli#239
- **Last Synced Status**: in_progress
- **Sanitized**: false
<!-- content_hash: local-sync-2026-07-08-module-runtime -->
