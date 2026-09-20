# Change: Module-Owned Bounded Turn Orchestration

## Why

Agents need a stable gate sequence, resumable local progress and a bounded review/fix loop. These capabilities must not create mandatory historical proof, obscure independent test/security/review outcomes or duplicate the optional preflight runtime.

## What Changes

- Add the module-owned `specfact workflow` group for pre-validate, implement state/checkpoints, verify, fix planning/recheck and opt-in local PR autofix.
- Preserve original producer artifacts and independent statuses; expose a normalized actionable findings view with producer references rather than extending Code Review schema 1.6 with ignored fields.
- Bind results to exact scoped content, configuration and tool identities. Separate run IDs from input digests; keep operational receipts local and resumable.
- Bound implementation repair to three iterations and PR repair to five rounds, with timeouts, no-progress stops, one controller, recovery and exact-head checks.
- Publish reusable prefixed workflow skills with the module; keep repository commands/settings and thin projection in the paired core adoption.

## Capabilities

### New Capabilities

- `turn-workflow-orchestration`: portable sequencing, producer adapters, current input identity and optional local progress.
- `bounded-pr-remediation`: local observation and explicitly authorized bounded PR repair with recoverable side effects.

### Modified Capabilities

None. Requirements, Code Review, governance envelopes, traceability and optional seal/conformance contracts remain owned by their existing changes.

## Impact

Planning only now. Later implementation adds `packages/specfact-workflow`, its manifest, registry entry, signed payload, tests and module command/usage documentation. Use existing core discovery/registration and public APIs with truthful core_compatibility; do not require an unreleased core consumer to publish the producer. Module skill content remains distinct from repository-owned wrapper projection and generic core #251 installation.

Requirements R09 remains pure reconciliation without Git, pytest or network calls. The new orchestration package is a separate executor/consumer. No new security taxonomy, evidence graph, seal service, hosted agent or model provider is required. Local validation works offline; selected GitHub governance and PR automation explicitly require live service access and cannot silently pass when unavailable.

## Dependencies and rollout

Modules #481 is the prerequisite for integrating its signed current-run Requirements contract. Standalone producer adapters can be developed independently, but publication with that integration waits for the compatible contract. The signed workflow publication blocks core #742 runtime adoption. The reverse core adoption is not a producer release prerequisite.

Related only: core #251/#253 skill distribution, core #740 policy cutover, core #247/modules #169 governance envelope, core #241/modules #171 graph, core #242/modules #170 traceability, parked core #522 findings taxonomy, and explicit optional preflight. These relationships do not create blanket runtime blockers. C15-specific review consumption waits for its own signed policy readiness; supported older producers retain their actual semantics without simulated C15 acceptance.

Deliver deterministic verification before local repair, and local repair before PR autofix. Publish through the canonical signed post-merge release path; candidate builds are test fixtures, not stable handoffs. Rollback disables the optional loop and restores the prior signed package/configuration without deleting original producer reports or relabeling old evidence.

Documentation impact: module command/reference and workflow guides on modules.specfact.io, installation/compatibility and CLI help; link the core contributor adoption with verified permalinks. Update navigation only for pages added at implementation.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #483
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/483>
- **Repository**: `nold-ai/specfact-cli-modules`
- **Parent Feature**: #163
- **Paired Core Story**: <https://github.com/nold-ai/specfact-cli/issues/742>
- **Last Synced Status**: proposed / Todo, 2026-09-20

## Signed Requirements compatibility gate

Before selecting or adopting workflow #483 for current-run Requirements integration, validate the exact immutable signed Requirements #481 publication and its schema-v3 `current_execution` contract against the actual core and workflow versions. Verify archive/manifest/payload signatures and identities, then exercise the exact installed pair with existing representative current-result fixtures. An absent, incompatible, unsigned or v2-only producer leaves runtime integration/adoption not ready; do not substitute a passing receipt or silently downgrade the contract. Repository skill projection remains independently deliverable, and core #740 retains policy cutover ownership.
