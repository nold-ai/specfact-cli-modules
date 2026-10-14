## ADDED Requirements

### Requirement: Bounded supplemental diagnostics
The trusted producer SHALL emit an opt-in bounded diagnostic sidecar from a validated report and authoritative per-side results before serialization, only for the authorized immutable public source pair. It SHALL preserve original report authority and failure exit, and SHALL exclude arbitrary analyzer text and private identifiers.

#### Scenario: Source-checked introduction
- **WHEN** an introduced finding has a signed-catalog rule and valid immutable public source location
- **THEN** the sidecar includes its rule, source digest, line and statically verified function without copying its message

#### Scenario: Incomplete evidence
- **WHEN** a field is unclassified, invalid, missing or truncated
- **THEN** the sidecar reports a finite unavailable category and never implies passing assurance

#### Scenario: Disabled or failed sidecar
- **WHEN** diagnostics are disabled or sidecar output fails
- **THEN** ordinary review findings and exit remain unchanged

### Requirement: Isolated single diagnostic execution
The existing customer workflow SHALL preserve ordinary PR, release and default dispatch paths and run only one non-matrix supplementary diagnostic job for explicit diagnostic dispatch. It SHALL verify the reviewed signed producer and immutable pair, retain all ten analyzers and existing sandbox and budget controls, and SHALL NOT satisfy the required native gate.

#### Scenario: Ordinary event
- **WHEN** a PR, release, push, workflow call or default dispatch occurs
- **THEN** existing customer behavior remains unchanged

#### Scenario: Explicit diagnostic dispatch
- **WHEN** the authorized preview is explicitly dispatched once
- **THEN** the single supplemental job executes the fixed pair and labels all results diagnostic-only
