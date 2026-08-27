## ADDED Requirements

### Requirement: Workflow phase contract

The canonical preflight workflow SHALL present the runtime phases in order and SHALL require a new snapshot and validation pass after any approved refinement.

#### Scenario: Finding is refined and rechecked

- **GIVEN** the review phase reports a correctable blocking finding
- **WHEN** the user approves the exact owning-artifact edit
- **THEN** the workflow returns to snapshot and validation
- **AND** prior readiness and approval state are discarded.

### Requirement: Workflow remains harness-neutral

The canonical workflow SHALL define intent, required CLI operations, evidence presentation, approval points, and stop conditions without assuming one harness file layout.

#### Scenario: Installer targets two harnesses

- **GIVEN** two compatible harnesses use different command and skill paths
- **WHEN** the same module-owned workflow is exported
- **THEN** each adapter may map invocation syntax and packaging
- **AND** both retain identical phase, approval, evidence, and stop semantics.

### Requirement: No implementation handoff without current verification

The workflow SHALL not hand off to an implementation command or agent unless the seal verifies against the current source snapshot.

#### Scenario: Source changes after approval

- **GIVEN** a contract was approved and sealed
- **WHEN** a bound OpenSpec artifact, dependency identity, repository revision, or approval-bound value changes
- **THEN** verification reports the seal stale
- **AND** the workflow returns to snapshot and validation instead of implementation.
