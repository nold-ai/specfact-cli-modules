# Change: Integrate released validation with Spec Kit and GitHub

## Why

Apply the owner-approved agentic SDLC roadmap to existing Python, OpenSpec/Spec Kit and GitHub users. Preserve the distinction between reviewed assertions, behavior evidence and authenticated authority. This is a bounded follow-up, not a replacement authoring or review engine.

## What Changes

- Thin upstream and CI invocation adapters: The modules repository SHALL provide an optional Spec Kit extension using documented pinned upstream extension hooks and a GitHub Actions integration invoking released SpecFact commands. Authoring, clarification and task generation SHALL remain upstream-owned. The integration SHALL verify compatible signed module/core identities and preserve producer exit codes and complete native reports. Hooks SHALL be documented as invocation assistance; protected CI SHALL remain the enforcement boundary. The first certified execution path SHALL use structured pytest runner identity, version and configuration, not unrestricted opaque command strings.
- Loss-aware summaries and SARIF projection: GitHub summaries SHALL show independent producer statuses, exact candidate identity, missing mappings, unavailable checks and native-report links. SARIF 2.1.0 projection SHALL include only suitable located findings and SHALL preserve stable rule identity, original rule/severity, producer identity and original report references. Unlocated obligations and unsupported evidence SHALL remain visible in summaries and authoritative native JSON. Projection SHALL NOT turn advisory convergence into acceptance, fabricate locations or overwrite failed test/security outcomes.
- Least-privilege portable integration: Integration defaults SHALL support local/offline native output without external writes or paid model calls. GitHub publication SHALL require only the scoped permissions needed for selected summary/artifact/code-scanning operations, with third-party actions pinned to immutable revisions. Pull-request execution SHALL NOT execute untrusted candidate code with write credentials through pull_request_target. Unsupported reviewer report formats SHALL be explicit; no universal CodeRabbit/Copilot SARIF contract SHALL be assumed. Native JSON SHALL remain available when code-scanning upload is unavailable.

## Capabilities

### New Capabilities

- `workflow-ecosystem-adapters`: integrate released validation with spec kit and github.

### Modified Capabilities

None in this proposal. Existing lean reconciliation and optional assurance retain their own ownership.

## Impact

Planning only in this PR; no runtime, registry, manifest or version changes. Modules owns thin extension/Actions packaging, producer projection and summaries. #483 owns execution/budgets; core #742 owns contributor adoption. Native JSON remains authoritative.

At implementation, update owning command help, adapter/reference and workflow guides on modules.specfact.io, README entry points where needed, frontmatter and navigation for added pages. Additive APIs remain optional; offline parsing/verification remains available. Rollback restores the prior compatible signed core/module pair and disables optional integration without rewriting historical reports.

## Dependencies and delivery

Current-run workflow integration waits for signed #483, which waits for #481. Spec Kit hook profile acceptance waits for paired compatibility follow-ups. Standalone summary/SARIF fixture work can proceed independently. Optional #433 and #169/#170/#171 are not blanket blockers.

Implementation follows specification, derived tests, meaningful failing-before evidence, code, passing evidence and scope-appropriate gates. Use current repository reality and live issue readiness before work; do not interpret this planning approval as authority to bypass an In Progress owner or signed release gate.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#492](https://github.com/nold-ai/specfact-cli-modules/issues/492)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/492>
- **Repository**: `nold-ai/specfact-cli-modules`
- **Parent Feature**: #163
- **Last Synced Status**: planning / Todo, 2026-10-04

## Research boundary

The roadmap and sources are in [AGENTIC_SDLC_ROADMAP.md](../../AGENTIC_SDLC_ROADMAP.md). Product priority is an owner decision. Productivity, savings, complete hidden-behavior detection and universal independent reviewer recall are not established claims.

## Planning validation

See [AGENTIC_SDLC_VALIDATION.md](../../AGENTIC_SDLC_VALIDATION.md) for actual proposal checks and the explicit Python-only analyzer applicability exception. Runtime review and release tasks remain pending.
