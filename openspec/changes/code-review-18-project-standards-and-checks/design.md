# Design for customer-owned standards and compatible review checks

## Canonical architecture

[Change 17 design](../code-review-17-project-runtime-bootstrap/design.md) owns the architecture, API sketch, trust decisions, alternatives, acceptance matrix and synthesis. This document records only this change's implementation responsibility. No runtime implementation or supported distribution is established here.

## Responsibility and data flow

Run native customer standards with their configured versions and plugins. Add the explicitly selected declarative profile extension, faithful supplemental analyzer environments, existing icontract analysis, and native explicit pytest selection.

Project selection/configuration is resolved before check execution. Explicit invocation/configuration wins over an explicitly selected organizational profile, which wins over native discovery. Native tools retain their own configuration and plugin semantics. Review owns findings/severity; the profile contributes declarative data only. Missing/incompatible selected providers are errors rather than an automatic fallback.

Use the single entrypoint namespace `specfact.project_profiles` for explicitly selected external CLI providers. A contribution carries its supported version, selection preferences, configuration paths and named argv commands. It does not create environments, define controller-bound worker objects or load arbitrary project providers into the CLI.

Project checks use project installations. Source-only supplemental tools use external tool environments. Import-dependent tools prefer a compatible project installation; otherwise prepare the exact same-interpreter project graph and origins with compatible analyzer dependencies externally. Never splice paths or upgrade a customer package to make a tool work. Record incompatible checks and remedies. Preserve unknown custom-check exits/output without invented finding positions.

The initial contract mechanism is existing icontract checked through CrossHair. Missing contracts are not applicable. Unsupported requested mechanisms and failures remain incomplete. Remove the implicit 80-percent customer floor and mandatory missing-icontract findings. SpecFact's own repository policy remains configured and enforced.

Issue #480 remains open until its actual behavior is demonstrated. Add native pytest regression cases for default/custom patterns, `tests/checks.py`, no conventional match, competing passing conventional tests, and mixed source/test selection. A selected failing test is not replaceable by a discovered passing test.

## Implementation reconciliation and first step

All implementation remains pending. Accepted interface or responsibility deviations must update the canonical design and this delta before handoff. Start by adding scenario-mapped behavior tests and capturing actual failing evidence. Preserve existing applicable governance while implementing the approved replacement.

## Risks and rollback

Wrong interpreter/source, dependency drift and overstated completion are the primary risks. Verify actual executable/source identities, native configuration and failure behavior. Keep an immutable compatible released pair for rollback. No permanent capsule backend remains in the replacement.
