## ADDED Requirements

### Requirement: Separate conformance command

The module SHALL expose a postimplementation conformance command that requires a valid preflight seal and explicit implementation identity and SHALL produce a distinct conformance result.

#### Scenario: No valid preflight seal exists

- **GIVEN** a change has no current valid preflight seal
- **WHEN** `specfact preflight conform <change-id>` is invoked
- **THEN** comparison does not proceed as successful conformance
- **AND** the user is directed to the pre-implementation review workflow.

### Requirement: Provenance-rich implementation evidence

The runtime SHALL capture or import changed paths, public interfaces, traceability, acceptance/test evidence, and extractor identities with exact revisions or digests.

#### Scenario: Historical test result is supplied for new implementation

- **GIVEN** test evidence does not bind to the selected implementation revision
- **WHEN** the runtime normalizes evidence
- **THEN** the evidence is stale or unverifiable
- **AND** it cannot satisfy a sealed acceptance or test-intent obligation.

### Requirement: Core conformance evaluation

The runtime SHALL delegate obligation comparison and drift semantics to the released core conformance interface and SHALL not invent additional success states in rendering.

#### Scenario: Core verifier returns unexpected drift

- **GIVEN** implementation includes a governed public change outside sealed scope
- **WHEN** conformance is evaluated and rendered
- **THEN** human and JSON output preserve the core unexpected finding and evidence identity
- **AND** rendering cannot convert it to conforming.

### Requirement: Explicit drift resolution paths

The workflow SHALL require the user to choose between correcting implementation and returning to preflight for contract refinement/reapproval when material drift is intentional.

#### Scenario: User accepts a new implementation behavior

- **GIVEN** conformance reports material unexpected or modified behavior
- **WHEN** the user decides the behavior is desired
- **THEN** the current conformance result remains non-passing
- **AND** the workflow returns to the preflight review loop for a new contract and seal.

### Requirement: Human and JSON parity

Conformance human and JSON renderers SHALL derive from the same normalized result and preserve seal, implementation, extractor, evidence, finding, and assurance-limit identities.

#### Scenario: Renderers process an unknown result

- **GIVEN** required evidence is unavailable
- **WHEN** both renderers emit output
- **THEN** each reports the same unknown status and missing evidence
- **AND** neither describes the implementation as conforming.

### Requirement: Atomic optional persistence

When explicitly requested, the runtime SHALL persist the implementation snapshot and conformance result atomically without modifying the original contract or seal.

#### Scenario: Persistence fails after comparison

- **GIVEN** the result is computed but the complete persistence set cannot be verified
- **WHEN** the command exits
- **THEN** no partial record is treated as durable conformance evidence
- **AND** the original preflight artifacts remain unchanged.

### Requirement: Opt-in delivery policy

The first conformance runtime SHALL remain opt-in and SHALL require a separate accepted policy change before becoming a universal blocking PR or archive gate.

#### Scenario: Repository has no conformance policy

- **GIVEN** the command is installed but no project policy requires it
- **WHEN** ordinary delivery proceeds
- **THEN** absence of a conformance run is reported as unavailable where queried
- **AND** the module does not silently create a new blocking merge rule.
