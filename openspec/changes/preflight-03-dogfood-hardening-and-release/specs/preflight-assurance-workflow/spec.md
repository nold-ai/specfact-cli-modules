## MODIFIED Requirements

### Requirement: Workflow phase contract

The stable canonical preflight workflow SHALL present the runtime phases in order, SHALL require a new snapshot and validation pass after any approved refinement, and SHALL retain regression evidence for every accepted dogfood defect affecting phase order, CLI delegation, approval, or stop behavior. It SHALL remain harness-neutral so downstream adapters preserve identical phase, approval, evidence, and stop semantics, and official execution SHALL load it from the signed installation path and verify the bound tuple of workflow version, workflow digest, and delegated CLI identity for the signed release.

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
