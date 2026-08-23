# paired-core-workflow-ref-trust Specification

## Purpose

Define event-specific trust boundaries for validation workflows that execute
paired core source, preserving matching-branch integration without allowing
manual runs to select arbitrary executable core refs.

## Requirements
### Requirement: Manual Runs Use Trusted Paired-Core Refs

Modules validation workflows that execute paired core source SHALL separate
manual-dispatch core selection from pull-request matching-branch validation.

#### Scenario: Pull request retains matching paired-core validation

- **GIVEN** a validation workflow runs for a non-manual event
- **WHEN** the same-named branch exists in the paired core repository
- **THEN** the workflow may resolve and check out that matching paired-core
  branch
- **AND** the checkout does not persist credentials.

#### Scenario: Manual main run uses core main

- **GIVEN** a validation workflow is manually dispatched from modules `main`
- **WHEN** it checks out paired core source
- **THEN** it uses the literal core `main` ref
- **AND** it does not evaluate a caller-selected core ref.

#### Scenario: Other manual runs use core dev

- **GIVEN** a validation workflow is manually dispatched from any modules ref
  other than `main`
- **WHEN** it checks out paired core source
- **THEN** it uses the literal core `dev` ref
- **AND** it does not evaluate a caller-selected core ref.

#### Scenario: Manual runs cannot reach the dynamic resolver

- **GIVEN** the event is `workflow_dispatch`
- **WHEN** workflow conditions are evaluated
- **THEN** the dynamic paired-core resolver and dynamic checkout are skipped
- **AND** exactly one literal paired-core checkout path is eligible.
