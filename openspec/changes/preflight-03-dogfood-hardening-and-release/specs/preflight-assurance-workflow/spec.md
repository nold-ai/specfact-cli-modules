## Scope rescope — 2026-09-20

Seal, checkpoint, frozen mapping, successor approval, and historical RED/GREEN requirements in this issue apply only when an explicitly selected assurance policy requests them. They are not prerequisites for ordinary implementation, Code Review, release promotion, skill installation, or generated instructions. Keep the internal optional-feature dependency chain and source/signature integrity. Missing optional chronology is not a failed current-execution claim. No runtime policy changes in this planning update. Remove the outgoing prerequisite imposed on modules C15 #417; preserve prerequisites #431/core #683 and consumers core #684/modules #434.

This owner-requested planning amendment supersedes conflicting default-workflow and dependency wording below; runtime behavior is unchanged. [Replacement policy](../../../requirements-09-minimal-evidence/proposal.md).

## MODIFIED Requirements

### Requirement: Workflow phase contract

When optional preflight assurance is explicitly selected, the stable canonical preflight workflow SHALL present the runtime phases in order, SHALL require a new snapshot and validation pass after any approved refinement, and SHALL retain regression evidence for every accepted dogfood defect affecting phase order, CLI delegation, approval, or stop behavior. It SHALL remain harness-neutral so downstream adapters preserve identical phase, approval, evidence, and stop semantics, and official execution SHALL load it from the signed installation path and verify the bound tuple of workflow version, workflow digest, and delegated CLI identity for the signed release.

#### Scenario: Finding is refined and rechecked

- **GIVEN** the review phase reports a correctable blocking finding
- **WHEN** the user approves the exact owning-artifact edit
- **THEN** the workflow returns to snapshot and validation
- **AND** prior readiness and approval state are discarded.

#### Scenario: Accepted workflow defect becomes a regression case

- **GIVEN** the core readiness decision accepts a reproducible workflow or CLI-delegation defect
- **WHEN** the stable candidate executes the mapped regression case
- **THEN** phase order, approval points, evidence presentation, and stop behavior match the corrected rule
- **AND** the test binds the canonical workflow and supported CLI identities.
