## ADDED Requirements

### Requirement: Bounded analyzer failure provenance

The existing Linux candidate and independent review diagnostic projections SHALL expose available analyzer side and fixed failure-class observations from readable private reports. They SHALL preserve unknown/unavailable values without inferring a fault from a finding location.

#### Scenario: Structured report preserves failure side and class

- **GIVEN** a readable structured report contains an incomplete analyzer on one recorded side and a recognized failure marker
- **WHEN** the existing workflow projects the failure
- **THEN** it emits the allowlisted analyzer, actual recorded side, and fixed failure-class observations without private messages or paths.

#### Scenario: Oversized report uses the same bounded interpretation

- **GIVEN** a report exceeds the ordinary size threshold but remains within the existing diagnostic bound
- **WHEN** existing validated report parsing succeeds
- **THEN** structured and oversized projections interpret the same provenance fields consistently without increasing any size or output limit.

#### Scenario: Unknown pytest failure remains unclassified

- **GIVEN** a pytest tool error has no recognized diagnostic marker
- **WHEN** its public location names the first selected source file
- **THEN** the projection reports an unclassified failure and does not claim that source file caused it or that a particular exception occurred.

#### Scenario: Native skip classification uses existing observations

- **GIVEN** an existing pytest observation records a known native-prerequisite skip detail
- **WHEN** the projection classifies that observation
- **THEN** it emits only the fixed prerequisite-not-supplied classification, and missing or unfamiliar details remain unavailable without host inspection or environment pass-through.

### Requirement: Finding lifecycle remains distinct from severity

The public projection SHALL retain validated existing finding lifecycle, status, and explicit blocking information. It SHALL NOT recompute differential classifications or turn missing blocking metadata into a non-blocking claim.

#### Scenario: Base-only fixed warning remains visible and non-blocking

- **GIVEN** the authoritative report retains a warning with differential state fixed and explicit blocking false
- **WHEN** the workflow emits its validated public location
- **THEN** the projection includes its fixed lifecycle and false blocking value without suppressing the finding or treating it as an active head failure.

#### Scenario: Active or missing blocking metadata preserves uncertainty

- **GIVEN** a report contains introduced or unchanged blocking findings, or has missing/invalid lifecycle or blocking metadata
- **WHEN** those findings are projected
- **THEN** valid blocking metadata remains visible, invalid fields are omitted or unavailable, and no new waiver or non-blocking default is created.

### Requirement: Diagnostic output preserves privacy bounds

The projection SHALL emit only existing validated locations, finite enums, strict Booleans, and existing bounded counts. It SHALL preserve parser, size, iteration, artifact, and output limits and SHALL treat private report contents as data.

#### Scenario: Private strings cannot enter public output

- **GIVEN** report fields contain seeded private paths, exception text, environment values, or arbitrary import names
- **WHEN** the projection reads the report
- **THEN** none of those strings appears in public output or newly uploaded artifacts and no subject-controlled code executes on the host.

#### Scenario: Malformed or oversized input fails closed

- **GIVEN** input violates an existing JSON, duplicate-key, size, shape, location, or iteration constraint
- **WHEN** the projection attempts to read it
- **THEN** it preserves existing refusal/bounded behavior and emits no raw fallback content or passing assurance.

### Requirement: Diagnostics cannot alter review authority

The diagnostic unit SHALL preserve all existing required jobs, tests, skips-as-failures, analyzer selection, budgets, admission, signatures, and review verdict/exit semantics. Candidate and independent reviewer identities SHALL remain separate and bound to the verified subject.

#### Scenario: Successful diagnostics leave a failed review blocking

- **GIVEN** a required review fails with incomplete analyzer evidence
- **WHEN** its diagnostic projection succeeds or itself fails
- **THEN** the captured review failure and required job remain blocking, and diagnostics cannot establish PASS, merge authority, or change completion.

#### Scenario: Evidence retains subject and reviewer identity

- **GIVEN** candidate and independent jobs analyze the same exact head using distinct reviewer implementations
- **WHEN** their diagnostic observations are collected
- **THEN** the observations retain those separate verified identities without accepting arbitrary report identity claims or substituting host reproduction for protected Linux evidence.
