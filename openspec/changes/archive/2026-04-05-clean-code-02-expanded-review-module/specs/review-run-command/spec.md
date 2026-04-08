## ADDED Requirements

### Requirement: Review run command orchestrates clean-code analysis
The bundle SHALL run the expanded clean-code analysis set as part of the governed review workflow.

#### Scenario: Review run includes clean-code categories in normal output
- **GIVEN** `specfact code review run --json <file>` executes with clean-code analysis enabled
- **WHEN** the run completes
- **THEN** the JSON report may contain findings in `naming`, `kiss`, `yagni`, `dry`, and `solid`
- **AND** the command keeps the same report envelope used by earlier runner changes

#### Scenario: PR mode runs checklist enforcement as advisory analysis
- **GIVEN** review run executes in PR mode
- **WHEN** checklist enforcement finds missing clean-code reasoning in the proposal or PR context
- **THEN** the report includes an advisory checklist finding
- **AND** the checklist finding does not create a new command surface
