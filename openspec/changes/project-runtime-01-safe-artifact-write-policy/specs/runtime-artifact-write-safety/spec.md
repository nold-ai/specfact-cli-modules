## ADDED Requirements

### Requirement: Bundle runtime commands SHALL use the core safe-write contract for user-project artifacts
Bundle commands that create or mutate persistent artifacts inside a user repository SHALL call the core safe-write contract instead of performing ad hoc overwrite logic.

#### Scenario: Runtime command writes owned artifact through safe-write helper
- **WHEN** a bundle command materializes or updates a persistent artifact in the user's repository
- **THEN** it SHALL call the core safe-write helper with declared ownership metadata
- **AND** SHALL NOT write the artifact through a raw overwrite path

#### Scenario: Unsupported merge falls back to explicit safe failure
- **WHEN** a bundle command targets an existing artifact whose format or ownership cannot be reconciled safely
- **THEN** the command SHALL fail with actionable guidance or require explicit replacement semantics
- **AND** SHALL leave the existing artifact unchanged by default

### Requirement: Runtime adoption SHALL be regression-tested against existing user content
Bundle commands that adopt the safe-write contract SHALL have regression tests proving that unrelated user content survives supported mutations.

#### Scenario: Partially owned runtime artifact preserves unrelated user content
- **WHEN** a regression fixture contains an existing user-managed artifact with additional custom content
- **AND** the bundle command updates only a SpecFact-managed section
- **THEN** the custom content SHALL remain intact
- **AND** only the managed section SHALL change
