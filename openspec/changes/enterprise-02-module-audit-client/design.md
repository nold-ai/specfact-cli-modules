# Design

## Context

The five-pillar enterprise design keeps server contracts out of scope for this wave, but it still needs a client-side audit bundle that can prepare, queue, sign, and inspect governance events. This module must interoperate with the paired core audit schema and with the enterprise policy client while remaining safe for disconnected or partially configured environments.

## Goals / Non-Goals

**Goals:**

- Define the package structure and command ownership for `specfact-enterprise-audit`.
- Emit signed, privacy-aware audit events aligned with the paired core schema.
- Support local queueing and retry/inspection behavior for events that cannot be delivered immediately.
- Keep event metadata structured enough for later reconciliation and drift analytics.

**Non-Goals:**

- Implement the enterprise audit service or server-side storage.
- Replace the paired core audit-event schema or RBAC semantics.
- Require immediate network delivery for every governance action.

## Decisions

### 1. Ship audit emission as its own enterprise bundle

- **Decision**: Create `packages/specfact-enterprise-audit/` with dedicated emission and inspection commands.
- **Why**: Audit transport, buffering, and event privacy are separate concerns from policy sync or base governance logic.
- **Alternative considered**: Combine audit behavior with the enterprise policy bundle. Rejected because it couples two independently deployable surfaces.

### 2. Queue first, deliver later when necessary

- **Decision**: The bundle records deterministic local queue metadata for events that cannot be delivered immediately.
- **Why**: Enterprise governance actions must not be lost because a remote endpoint is temporarily unavailable.
- **Alternative considered**: Fail the originating action whenever the audit backend is unavailable. Rejected because it creates brittle runtime behavior for disconnected workflows.

### 3. Keep payloads privacy-aware by design

- **Decision**: Audit payloads include structured event metadata and references, not raw sensitive content.
- **Why**: Audit surfaces must preserve accountability without leaking governed data.
- **Alternative considered**: Store raw payload snapshots for debugging. Rejected because it conflicts with the security/privacy posture of the broader platform.

## Risks / Trade-offs

- **Risk**: Local queue growth may become operationally noisy. → **Mitigation**: provide inspection commands and deterministic receipt/retention metadata.
- **Risk**: Delivery semantics may evolve with the future server implementation. → **Mitigation**: keep this change focused on client-side event preparation and queueing contracts.
- **Risk**: Overly sparse payloads could weaken audit usefulness. → **Mitigation**: preserve event type, actor role, target references, and source rule/policy identifiers in the schema mapping.

## Migration Plan

1. Confirm the paired core audit/RBAC contracts are stable enough for module integration.
2. Implement package structure, signing helpers, queue storage, and inspection commands.
3. Publish docs, registry metadata, signatures, and compatibility range together.

## Open Questions

- Which queue storage format best balances resilience and inspectability for the initial release?
- How should retry cadence and dead-letter behavior be surfaced in the first client contract?