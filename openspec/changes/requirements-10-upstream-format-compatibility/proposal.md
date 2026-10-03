# Change: Refresh native upstream artifact compatibility

## Why

Apply the owner-approved agentic SDLC roadmap to existing Python, OpenSpec/Spec Kit and GitHub users. Preserve the distinction between reviewed assertions, behavior evidence and authenticated authority. This is a bounded follow-up, not a replacement authoring or review engine.

## What Changes

- Pinned upstream artifact profiles: The adapter SHALL test pinned Spec Kit v1.1.0 fixtures alongside retained v0.12.18 and supported OpenSpec fixtures. Fixture metadata SHALL identify upstream tag/commit, artifact paths and content digests. Support SHALL be evaluated from the effective artifact profile, including enabled known extensions and template resolution, rather than inferred from Markdown or a claimed CLI version. The supported profile allowlist SHALL be explicit and versioned; unknown or unsupported custom profiles SHALL be rejected with an actionable diagnostic.
- Extension coexistence and atomic import: A supported SpecFact extension that only adds invocation hooks SHALL NOT by its presence invalidate a supported native artifact profile. An extension that alters artifact templates SHALL require a tested effective profile. Import and readiness validation SHALL complete before persistence; any profile, parse or readiness failure SHALL leave existing imported state unchanged. Import SHALL remain offline and SHALL NOT execute upstream scripts, fetch templates or rewrite upstream inputs.

## Capabilities

### New Capabilities

- `upstream-format-compatibility-runtime`: refresh native upstream artifact compatibility.

### Modified Capabilities

None in this proposal. Existing lean reconciliation and optional assurance retain their own ownership.

## Impact

Planning only in this PR; no runtime, registry, manifest or version changes. Modules owns effective-profile command integration, atomic persistence tests, compatibility metadata and signed Requirements publication. Shared profile parsing belongs to paired core.

At implementation, update owning command help, adapter/reference and workflow guides on modules.specfact.io, README entry points where needed, frontmatter and navigation for added pages. Additive APIs remain optional; offline parsing/verification remains available. Rollback restores the prior compatible signed core/module pair and disables optional integration without rewriting historical reports.

## Dependencies and delivery

Signed runtime adoption waits for the compatible core upstream-format contract. It does not block #481/#483 base delivery; the new invocation extension is enabled only after its exact profile is certified.

Implementation follows specification, derived tests, meaningful failing-before evidence, code, passing evidence and scope-appropriate gates. Use current repository reality and live issue readiness before work; do not interpret this planning approval as authority to bypass an In Progress owner or signed release gate.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#490](https://github.com/nold-ai/specfact-cli-modules/issues/490)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/490>
- **Repository**: `nold-ai/specfact-cli-modules`
- **Parent Feature**: #161
- **Last Synced Status**: planning / Todo, 2026-10-04

## Research boundary

The roadmap and sources are in [AGENTIC_SDLC_ROADMAP.md](../../AGENTIC_SDLC_ROADMAP.md). Product priority is an owner decision. Productivity, savings, complete hidden-behavior detection and universal independent reviewer recall are not established claims.

- **Paired Core Story**: [nold-ai/specfact-cli#749](https://github.com/nold-ai/specfact-cli/issues/749)

## Planning validation

See [AGENTIC_SDLC_VALIDATION.md](../../AGENTIC_SDLC_VALIDATION.md) for actual proposal checks and the explicit Python-only analyzer applicability exception. Runtime review and release tasks remain pending.
