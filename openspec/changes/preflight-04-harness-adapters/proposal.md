# Change: Plug-and-Play Preflight Harness Adapters

## Why

The stable preflight workflow should be installable in compatible agent harnesses without copying validator logic or maintaining divergent workflow prose. Codex, Everything Claude Code (ECC), and hatch3r are the first integration targets because they already expose skills, commands or plugins, and cross-harness instruction surfaces with different packaging conventions.

## What Changes

- **NEW**: A later Codex plugin package that installs the released module-owned preflight skill and exposes the native Codex invocation form.
- **NEW**: A later ECC companion integration that treats the skill as canonical and adds a command shim only where ECC compatibility requires it.
- **NEW**: A later hatch3r pack/inventory integration that maps the canonical workflow into hatch3r's currently supported generated adapters.
- **NEW**: Shared adapter descriptors for source module identity, harness/version compatibility, invocation mapping, installed asset inventory, upgrade/uninstall behavior, and drift checks.
- **CLARIFY**: Adapters call the same released SpecFact CLI and consume the same result schema. They do not embed, fork, translate, or replace Python validators.

## Capabilities

### New Capabilities

- `preflight-harness-adapters`: Thin, versioned installation and invocation adapters for Codex, ECC, and hatch3r.

### Modified Capabilities

(none)

## Impact

- Planning artifacts only in this phase. No plugin, skill file, command shim, pack, manifest, hook, workflow, dependency, publication artifact, or external repository contribution is created.
- Future implementation consumes the stable signed module workflow, core #251 installation/export behavior, and core #253 generated instruction contract.
- Each external repository contribution requires its own accepted upstream issue/PR and must preserve that project's current contribution and packaging rules.

## Dependencies

- Parent Feature: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163).
- Blocked by core `ai-integration-03-instruction-files` [#253](https://github.com/nold-ai/specfact-cli/issues/253), which is blocked by #251 and the stable preflight module handoff.
- Consumes the signed module identity from paired modules `preflight-03-dogfood-hardening-and-release` transitively; no feature-branch asset may be packaged.

## Explicit Non-Goals

- No new validators, readiness policy, contract schema, approval behavior, or conformance logic.
- No hooks that bypass explicit user approval or automatically edit source artifacts.
- No promise of harness support beyond versions and platforms proved by adapter tests.
- No external repository write or publication during this planning-only setup.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #433
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/433>
- **Last Synced Status**: proposed
- **Sanitized**: true
