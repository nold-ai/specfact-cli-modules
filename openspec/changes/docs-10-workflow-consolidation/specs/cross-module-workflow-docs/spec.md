# Capability: cross-module-workflow-docs

Documented end-to-end flows showing how to chain commands across multiple bundles.

## Scenarios

### Scenario: Cross-module chain covers full lifecycle

Given the cross-module-chains workflow doc
When a user reads the page
Then it shows a complete flow: backlog ceremony -> code import -> spec validate -> govern enforce
And each step shows the exact command with practical arguments

### Scenario: Daily routine covers a full work day

Given the daily-devops-routine workflow doc
When a user reads the page
Then it shows: morning standup, refinement, development, review, and end-of-day patterns
And each step links to the relevant bundle command reference

### Scenario: CI pipeline doc covers automation patterns

Given the ci-cd-pipeline workflow doc
When a user reads the page
Then it shows: pre-commit hooks, GitHub Actions integration, and CI/CD stage mapping
And all specfact commands shown are valid and current
