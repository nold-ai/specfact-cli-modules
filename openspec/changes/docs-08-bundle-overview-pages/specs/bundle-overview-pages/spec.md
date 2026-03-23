# Capability: bundle-overview-pages

Each official bundle has a single overview page listing all commands, prerequisites, and quick examples.

## Scenarios

### Scenario: Overview page lists all bundle commands

Given a bundle overview page (e.g., bundles/backlog/overview.md)
When a user reads the page
Then every registered command and subcommand for that bundle is listed
And each command has a brief description

### Scenario: Overview page includes quick examples

Given a bundle overview page
When a user reads the page
Then at least one practical example is shown for each major command group

### Scenario: Command examples match actual CLI

Given a command example in an overview page
When compared against the actual `specfact <command> --help` output
Then the command name, arguments, and key options match
