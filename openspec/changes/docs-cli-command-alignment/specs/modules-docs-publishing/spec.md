## MODIFIED Requirements

### Requirement: Modules docs site is the canonical home for official bundle documentation

The modules documentation site SHALL present itself as the canonical published home for official bundle and module-specific deep documentation, and its command examples SHALL match the currently mounted CLI surface shipped with the official modules.

#### Scenario: Reader follows a command example from the modules docs

- **WHEN** a reader copies a command example from the modules docs reference or installation pages
- **THEN** the example uses a command path that is currently mounted in `specfact --help`
- **AND** the example does not rely on removed top-level shims such as flat `sync`, `repro`, `validate`, or `enforce` command groups when the mounted path is nested under another group
- **AND** official bundle install examples use the current published module ids from `specfact-cli-modules`
