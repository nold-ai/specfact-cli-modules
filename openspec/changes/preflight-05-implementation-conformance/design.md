## Context

This paired modules change executes the core conformance contract after implementation. It deliberately has a different command, result, policy phase, and evidence boundary from `specfact preflight run` so pre-implementation approval cannot be mistaken for delivery proof.

## Goals / Non-Goals

**Goals:**

- Capture exact implementation and test evidence without mutating the sealed contract.
- Evaluate approved obligations and unexpected drift through the released core verifier.
- Give humans and agents one actionable, provenance-rich result before PR/archive decisions.
- Require explicit reapproval when implementation intentionally changes the contract.

**Non-Goals:**

- Implement general code review, coverage, architecture analysis, or security scanning already owned elsewhere.
- Generate missing tests or change production code.
- Treat unavailable evidence as success.

## Decisions

### 1. Separate command and result lifecycle

`specfact preflight conform <change-id>` requires a preflight seal that verifies against its sealed contract and base source snapshot plus an explicit implementation identity in the released core snapshot format. The implementation base/head or exact range is supplied separately; a missing, implicit, or ambiguous identity is rejected. Implementation commits do not by themselves invalidate the base-bound seal, and the command produces a conformance result rather than a new preflight readiness result or altered seal.

### 2. Evidence adapters reuse existing outputs

The runtime imports exact repository diff manifests, interface/traceability records, and current-run test evidence from existing SpecFact contracts where available. It records producer/version/digest and does not reimplement those analyzers. Missing required evidence yields unknown or blocking conformance according to policy.

### 3. Closed mapping validators

Python validators map sealed scope, exclusions, interfaces, acceptance criteria, test intent, and tasks to normalized implementation evidence. They emit only the core drift classes and retain source/evidence paths for remediation.

### 4. Human decides drift resolution

For unexpected or modified implementation, the workflow offers two explicit paths: correct the implementation to the sealed contract, or return to preflight to review/refine/reapprove the contract. It cannot mark intentional drift accepted by itself.

### 5. Delivery integration remains opt-in

The first release provides command and workflow evidence without making every PR gate depend on it. A later policy change may require conformance for selected projects only after dogfood demonstrates usable signal.

## Risks / Trade-offs

- **Duplicate analyzer ownership:** Import existing normalized evidence rather than running parallel analyzers.
- **Mapping noise:** Require exact contract paths and evidence identities; preserve unknowns.
- **Approval confusion:** Keep separate command/result vocabulary and never reseal from conform.
- **Premature blocking rollout:** Start opt-in and require a later policy decision for enforcement.

## Migration and Rollback

The command is additive and optional. Removing the conformance module surface leaves the original preflight contract/seal unchanged. Persisted conformance results can be deleted without invalidating pre-implementation approval identity; delivery policy must then treat conformance as unavailable, not passed.

## Open Questions Deferred to Implementation

- Which existing test/traceability evidence schemas are mandatory for the first supported profile.
- Retention policy for multiple conformance runs against one seal.
