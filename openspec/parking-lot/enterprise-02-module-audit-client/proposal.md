# Change: Enterprise Audit Client Module

## Why

The enterprise add-on needs a client-side runtime that emits signed audit events for rule promotion, policy sync, approvals, and related governance actions. Without a dedicated audit bundle, enterprise RBAC and audit-trail contracts cannot be exercised by the modules-side runtime.

## What Changes

- **NEW**: Add a `specfact-enterprise-audit` bundle with commands and helpers for audit event emission and queue inspection.
- **NEW**: Package signed audit-event preparation, buffering, and retry behavior compatible with the paired core audit schema.
- **NEW**: Add privacy-aware handling so audit payloads carry event metadata without leaking restricted content.
- **NEW**: Define deterministic local queue/receipt metadata for events awaiting delivery or reconciliation.
- **EXTEND**: Reserve manifest, registry, docs, and signing work for a first-party enterprise audit bundle.

## Capabilities

### New Capabilities

- `enterprise-audit-client`: Runtime bundle, signed audit event emission, and local queue/inspection surfaces for enterprise governance actions.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-enterprise-audit/`, signing/queue helpers, and audit inspection commands.
- Affected docs: bundle overview and command-reference documentation for enterprise audit workflows.
- Dependencies: paired core change `enterprise-02-rbac-and-audit-trail`; related sequencing from `enterprise-01-module-policy-client`.
- Release impact: introduces a new signed official bundle and registry entry intended for enterprise deployments.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#222](https://github.com/nold-ai/specfact-cli-modules/issues/222)
- **GitHub Issue**: [#232](https://github.com/nold-ai/specfact-cli-modules/issues/232)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/232>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
