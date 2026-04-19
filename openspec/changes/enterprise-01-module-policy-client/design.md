## Context

Enterprise policy push belongs to a client-side module in this repo because the server component is explicitly out of scope for the five-pillar OpenSpec wave. This bundle needs to fetch signed payloads, cache them locally, and expose inspection commands while preserving the product’s no-op behavior for users who are not connected to an enterprise endpoint.

## Goals / Non-Goals

**Goals:**

- Define the package structure and command ownership for `specfact-enterprise-policy`.
- Verify and cache pushed policy payloads before they affect local resolution behavior.
- Keep enterprise policy support additive so unconfigured users continue to operate normally.
- Provide deterministic local metadata showing when and how policy layers were applied.

**Non-Goals:**

- Implement the enterprise policy server itself.
- Replace the paired core resolution-chain semantics.
- Require enterprise connectivity for base product behavior.

## Decisions

### 1. Ship policy sync as an enterprise-only bundle

- **Decision**: Create `packages/specfact-enterprise-policy/` with dedicated sync/status commands.
- **Why**: Enterprise policy pull should remain optional and separately installable from the base platform.
- **Alternative considered**: Fold policy sync into `specfact-govern`. Rejected because it mixes enterprise transport concerns into a general governance bundle.

### 2. Verify before apply

- **Decision**: The bundle validates signed payload metadata before cached policies influence local resolution.
- **Why**: Enterprise policy push is only trustworthy if the client can reject tampered or stale payloads.
- **Alternative considered**: Apply first and verify lazily. Rejected because it weakens the core governance posture.

### 3. No configured endpoint means explicit no-op behavior

- **Decision**: When enterprise configuration is absent, the bundle surfaces that status clearly and does not alter local resolution behavior.
- **Why**: Free-tier and offline users must not experience degraded UX because enterprise support exists.
- **Alternative considered**: Treat missing configuration as an error. Rejected because it violates additive-tier semantics.

## Risks / Trade-offs

- **Risk**: Policy payload caching can drift from server state. → **Mitigation**: cache metadata must include freshness and signature details, and sync/status commands expose drift clearly.
- **Risk**: Misconfiguration could create confusing mixed-mode behavior. → **Mitigation**: explicit status surfaces distinguish active, stale, and no-op states.
- **Risk**: Transport/security details could change with the eventual server implementation. → **Mitigation**: keep the bundle contract focused on verified payload consumption, not server internals.

## Migration Plan

1. Confirm the paired core resolution-chain extension is stable enough for integration.
2. Implement package structure, transport/cache helpers, and sync/status commands.
3. Publish docs, registry metadata, signatures, and compatibility range together.

## Open Questions

- Which transport/auth mechanism should be assumed in the initial client contract without overcommitting to server internals?
- How much offline cache retention policy needs to be codified in the first release?
