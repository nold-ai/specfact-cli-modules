## MODIFIED Requirements

### Requirement: Finalized Requirements Evidence Review Context

Code Review SHALL retain finalized `current_execution` and optional `red_green_chronology` claims as separate provenance, including their digests, statuses, evidence references, verifier epoch, and limitations. It SHALL NOT use either Requirements claim to calculate review findings, score, verdict, or exit code.

#### Scenario: Bounded chronology is visible but independent

- **GIVEN** finalized Requirements evidence contains a trusted R08 chronology capsule
- **WHEN** Code Review consumes the evidence
- **THEN** the report retains the capsule digest, bounded claim, and limitations
- **AND** review policy remains derived only from review evidence.

