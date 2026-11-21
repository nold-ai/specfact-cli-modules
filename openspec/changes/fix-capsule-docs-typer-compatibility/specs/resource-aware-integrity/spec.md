## ADDED Requirements

### Requirement: Start the published core in both capsule environments

Both capsule installations SHALL use the published SpecFact CLI 0.55.4 with a compatible Typer version.

#### Scenario: Published CLI starts in each capsule job

- **GIVEN** a fresh customer or independent reviewer environment
- **WHEN** the job installs the published core and starts its module command
- **THEN** the CLI starts and the existing module installation checks run
