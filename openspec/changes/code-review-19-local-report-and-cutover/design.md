# Design for local review evidence and capsule removal

## Canonical architecture

[Change 17 design](../code-review-17-project-runtime-bootstrap/design.md) owns the architecture, API sketch, trust decisions, alternatives, acceptance matrix and synthesis. This document records only this change's implementation responsibility. No runtime implementation or supported distribution is established here.

## Responsibility and data flow

Introduce local schema 2.0 with explicit consumers and source-bound execution. Preserve useful scope/differential behavior and perform the single public cutover that deletes capsule execution and the legacy host orchestrator.

Create an explicit local report schema 2.0. Carry source/dependency/configuration/tool identities and per-check completion with findings independently. Update modules-side pre-commit/report helpers and compatibility fixtures together. The paired core change updates ordinary core consumers. Current `major > 1 or ... >= 1.6` helpers must not choose the legacy handler for 2.0. Reject unrecognized report versions, including unsupported minor versions within a known major, and malformed required evidence.

Keep worktree/index/range/full/explicit selection, source spans, identity/multiset/differential logic and suppression comparison where compatible. Match check/policy identities for comparisons. A worktree source change invalidates the result. Index/range preparations bind each source snapshot; a live editable import, generated file or native artifact from another checkout cannot supply snapshot execution evidence.

Completed failing tests remain findings. Missing required checks, failed preparation, malformed output and timeout remain incomplete and nonaccepting outside shadow. Shadow preserves adverse truth. Do not introduce C15 calibration, suppression approval authority, or schema 1.7 promises here.

Perform the public runner switch and production deletions in one cutover. Adapt useful pure helpers rather than redirecting to the existing SpecFact-specific host runner. Delete callable native macOS and Linux OCI/Bubblewrap paths, capsule acquisition, brokers, import policing, sealed dependency/native-library copying, catalogs and permanent fallback toggles. Later distribution cleanup may remove residue but cannot leave a callable old runtime. Preserve module signatures, source integrity, process timeouts and independent security gates.

The implementation delta must explicitly remove/replace applicable capsule requirements before archival. Neither local immutable scope nor caller PR context creates protected `pr_range`; existing core #680 remains a separate incompatible protected contract. Historical artifacts and report readers retain original semantics.

## Implementation reconciliation and first step

All implementation remains pending. Accepted interface or responsibility deviations must update the canonical design and this delta before handoff. Start by adding scenario-mapped behavior tests and capturing actual failing evidence. Preserve existing applicable governance while implementing the approved replacement.

## Risks and rollback

Wrong interpreter/source, dependency drift and overstated completion are the primary risks. Verify actual executable/source identities, native configuration and failure behavior. Keep an immutable compatible released pair for rollback. No permanent capsule backend remains in the replacement.
