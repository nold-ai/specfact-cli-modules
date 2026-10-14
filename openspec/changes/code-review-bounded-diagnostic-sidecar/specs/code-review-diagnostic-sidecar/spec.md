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

### Requirement: Durable host-only progress
The actual installed full-review process SHALL verify signed payload and imported source identities before emitting `verified_review_entry`. Its private atomic `progress.json` SHALL contain immutable producer, payload, workflow, supervisor, nonce and fixed subject identities, finite latest stage and at most twenty side/member cells. Guest adapter identity and effective deadline SHALL remain UNAVAILABLE. Host stage entry SHALL NOT establish guest execution or analyzer cause.

#### Scenario: Blocking first member
- **WHEN** the host enters snapshot preparation or dispatches a member that blocks
- **THEN** a complete bounded checkpoint exists before the blocking call and survives termination

#### Scenario: Invalid or disabled progress
- **WHEN** identity is absent/mismatched, a record is malformed, oversized, linked or contains unknown/private fields, or diagnostics are disabled
- **THEN** observations remain unavailable, no unsafe text is emitted and original review behavior remains unchanged

### Requirement: Owned bounded supervisor
The outer supervisor SHALL launch a new owned session/group, write separately owned atomic `terminal.json`, distinguish child exit124 from wrapper expiry, bound TERM and KILL/reap to five seconds each, avoid inherited pipe drains, and preserve failed exit. The collector SHALL independently validate closed schemas and identities before emitting bounded diagnostic-only summary.

#### Scenario: Expiry with inherited pipes
- **WHEN** the child exceeds its wrapper deadline while a descendant holds pipes
- **THEN** only the owned group is terminated within bounded cleanup while the supervisor and unrelated sibling survive

#### Scenario: Signed smoke prerequisite
- **WHEN** the exact signed installed producer enters its real full-review entry and host dispatcher with a synthetic stalled member on supported Linux
- **THEN** early identity/progress and owned cleanup are proven within120seconds including cleanup before the single full experiment; failure stops without retry
