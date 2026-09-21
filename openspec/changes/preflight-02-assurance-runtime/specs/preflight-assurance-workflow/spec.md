## Scope rescope — 2026-09-20

Seal, checkpoint, frozen mapping, successor approval, and historical RED/GREEN requirements in this issue apply only when an explicitly selected assurance policy requests them. They are not prerequisites for ordinary implementation, Code Review, release promotion, skill installation, or generated instructions. Keep the internal optional-feature dependency chain and source/signature integrity. Missing optional chronology is not a failed current-execution claim. No runtime policy changes in this planning update. Remove the outgoing prerequisite imposed on core C14 #680; core dogfood #683 still requires this runtime explicitly.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../../../requirements-09-minimal-evidence/proposal.md).

## ADDED Requirements

### Requirement: Workflow phase contract

When optional preflight assurance is explicitly selected, the canonical preflight workflow SHALL present the runtime phases in order and SHALL require a new snapshot and validation pass after any approved refinement.

#### Scenario: Finding is refined and rechecked

- **GIVEN** the review phase reports a correctable blocking finding
- **WHEN** the user approves the exact owning-artifact edit
- **THEN** the workflow returns to snapshot and validation
- **AND** prior readiness and approval state are discarded.

### Requirement: Workflow remains harness-neutral

When optional preflight assurance is explicitly selected, the canonical workflow SHALL define intent, required CLI operations, evidence presentation, approval points, and stop conditions without assuming one harness file layout.

#### Scenario: Installer targets two harnesses

- **GIVEN** two compatible harnesses use different command and skill paths
- **WHEN** the same module-owned workflow is exported
- **THEN** each adapter may map invocation syntax and packaging
- **AND** both retain identical phase, approval, evidence, and stop semantics.

### Requirement: No implementation handoff without current verification

When optional preflight assurance is explicitly selected, the workflow SHALL not hand off to an implementation command or agent unless the seal verifies against the current source snapshot.

#### Scenario: Source changes after approval

- **GIVEN** a contract was approved and sealed
- **WHEN** a bound OpenSpec artifact, dependency identity, repository revision, or approval-bound value changes
- **THEN** verification reports the seal stale
- **AND** the workflow returns to snapshot and validation instead of implementation.

#### Scenario: Ordinary delivery has not selected preflight assurance

- **GIVEN** no applicable assurance policy selects preflight approval for the change
- **WHEN** ordinary MEB implementation or delivery is evaluated
- **THEN** a missing preflight seal or approval source SHALL NOT block that workflow
- **AND** no preflight verification success is claimed; current tests and existing integrity checks still apply.
