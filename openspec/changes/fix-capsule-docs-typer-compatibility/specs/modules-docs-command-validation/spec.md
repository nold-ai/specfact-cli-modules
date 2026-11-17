## ADDED Requirements

### Requirement: Preserve command overview argument labels

The command overview generator SHALL preserve explicit argument metavars and render default labels from declared argument names.

#### Scenario: Generate labels without the legacy Typer property

- **GIVEN** a Typer command with a declared positional argument
- **WHEN** the command overview generator renders the argument
- **THEN** the label is the explicit metavar or the uppercase declared name
