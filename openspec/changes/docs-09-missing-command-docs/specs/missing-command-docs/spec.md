## ADDED Requirements

### Requirement: Missing command reference pages SHALL document the implemented command surface
Previously undocumented command pages SHALL describe the current option surface, examples, and relevant bundle-owned resource guidance for their commands.

#### Scenario: Each command page documents full option reference
- **GIVEN** a command reference page such as `bundles/govern/enforce.md`
- **WHEN** a user reads the page
- **THEN** every option and argument from the command's `--help` output is documented
- **AND** practical examples demonstrate common usage patterns

#### Scenario: Command pages explain bundle-owned resources where they affect usage
- **GIVEN** a command reference page for a command that depends on migrated bundle-owned prompts or templates
- **WHEN** a user reads the page
- **THEN** the page explains the relevant setup or bootstrap path
- **AND** it does not direct users to legacy core-owned resource locations

#### Scenario: Spec bundle has complete documentation
- **GIVEN** the spec bundle overview links to deep-dive pages
- **WHEN** a user follows links to validate, generate-tests, and mock
- **THEN** each page exists and contains command reference, examples, and related commands

#### Scenario: Govern bundle has complete documentation
- **GIVEN** the govern bundle overview links to deep-dive pages
- **WHEN** a user follows links to enforce and patch
- **THEN** each page exists and contains command reference, examples, and related commands

#### Scenario: Code review bundle has complete documentation
- **GIVEN** the code-review bundle overview links to deep-dive pages
- **WHEN** a user follows links to run, ledger, and rules
- **THEN** each page exists and contains command reference, examples, and related commands
