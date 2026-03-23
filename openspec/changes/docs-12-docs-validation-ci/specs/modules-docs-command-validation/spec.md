# Capability: modules-docs-command-validation

CI validation that module docs command examples match actual bundle implementations.

## Scenarios

### Scenario: Valid command example passes

Given a docs page references `specfact backlog ceremony standup`
When the validation runs
Then it finds a matching registration in the backlog package source
And the check passes

### Scenario: Invalid command example fails

Given a docs page references `specfact backlog nonexistent`
When the validation runs
Then it reports the mismatch
And the check fails
