# Capability: missing-command-docs

Reference documentation for all previously undocumented commands across spec, govern, code-review, and codebase bundles.

## Scenarios

### Scenario: Each command page documents full option reference

Given a command reference page (e.g., bundles/govern/enforce.md)
When a user reads the page
Then every option and argument from the command's --help output is documented
And practical examples demonstrate common usage patterns

### Scenario: Spec bundle has complete documentation

Given the spec bundle overview links to deep-dive pages
When a user follows links to validate, generate-tests, and mock
Then each page exists and contains command reference, examples, and related commands

### Scenario: Govern bundle has complete documentation

Given the govern bundle overview links to deep-dive pages
When a user follows links to enforce and patch
Then each page exists and contains command reference, examples, and related commands

### Scenario: Code review bundle has complete documentation

Given the code-review bundle overview links to deep-dive pages
When a user follows links to run, ledger, and rules
Then each page exists and contains command reference, examples, and related commands
