## MODIFIED Requirements

### Requirement: Team setup docs SHALL cover operational onboarding and resource ownership

Team setup guidance SHALL explain onboarding, shared configuration, role-based workflows, and how bundle-owned prompts/templates are rolled out and kept in sync.

#### Scenario: Team setup guide covers onboarding

- **GIVEN** the `team-collaboration` doc
- **WHEN** a team lead reads the page
- **THEN** it covers initial team setup, shared configuration, role-based workflows, and recommended collaboration patterns

#### Scenario: Team docs explain bundle-owned resource rollout

- **GIVEN** the team setup docs
- **WHEN** a team lead reads the page
- **THEN** the docs explain that prompts and bundle-specific workspace templates ship from installed bundles
- **AND** they describe how teams keep those resources aligned through supported bootstrap commands and version management
