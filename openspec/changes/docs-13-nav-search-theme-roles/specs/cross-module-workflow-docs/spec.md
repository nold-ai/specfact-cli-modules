# Specs - Cross Module Workflow Docs

## MODIFIED Requirements

### Requirement: Workflow docs SHALL cover current cross-module flows and setup prerequisites

Workflow documentation SHALL show valid multi-bundle command chains and include resource-bootstrap steps when migrated bundle-owned prompts or templates are prerequisites. The sidebar Workflows section SHALL link to all workflow pages.

#### Scenario: Cross-module chain covers full lifecycle

- **GIVEN** the `cross-module-chains` workflow doc
- **WHEN** a user reads the page
- **THEN** it shows a complete flow such as backlog ceremony -> code import -> spec validate -> govern enforce
- **AND** each step shows the exact command with practical arguments

#### Scenario: Workflow docs explain resource bootstrap before dependent flows

- **GIVEN** a workflow doc that uses AI IDE prompts or backlog workspace templates
- **WHEN** a user reads the page
- **THEN** the workflow includes the supported resource bootstrap step such as `specfact init ide`
- **AND** it does not rely on legacy core-owned resource paths

#### Scenario: CI pipeline doc covers automation patterns

- **GIVEN** the `ci-cd-pipeline` workflow doc
- **WHEN** a user reads the page
- **THEN** it shows pre-commit hooks, GitHub Actions integration, and CI/CD stage mapping
- **AND** all SpecFact commands shown are valid and current

#### Scenario: Sidebar Workflows section links to all workflow pages

- **WHEN** the Workflows section is rendered in the sidebar
- **THEN** it SHALL include links to Cross-Module Chains, Daily DevOps Routine, CI/CD Pipeline, and Brownfield Modernization
- **AND** it SHALL include links to existing workflow pages (Agile & Scrum, Command Chains, Common Tasks, Copilot Mode, Contract Testing)
