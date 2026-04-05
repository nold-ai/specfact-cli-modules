## MODIFIED Requirements

### Requirement: Workflow docs SHALL document a current daily development routine

Workflow documentation SHALL provide a complete day-level routine that links standup, backlog refinement, development, review, and release readiness to the current bundle command surface.

#### Scenario: Daily routine covers a full work day

- **GIVEN** the `daily-devops-routine` workflow doc
- **WHEN** a user reads the page
- **THEN** it shows morning standup, refinement, development, review, and end-of-day patterns
- **AND** each step links to the relevant bundle command reference
