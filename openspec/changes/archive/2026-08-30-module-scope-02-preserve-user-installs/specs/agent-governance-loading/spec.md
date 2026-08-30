## ADDED Requirements

### Requirement: Repository bootstrap guidance preserves user-scoped modules

Contributor and agent bootstrap guidance SHALL treat project-over-user module shadowing as workspace-local precedence and SHALL NOT prescribe deletion of the shadowed user-scoped installation as routine cleanup.

#### Scenario: Project module shadows a user installation

- **GIVEN** the same module id is installed in project scope and user scope
- **WHEN** an agent loads repository bootstrap or module-scope guidance
- **THEN** the guidance states that project scope takes precedence inside the current repository
- **AND** the guidance states that the user-scoped copy remains installed and usable outside the repository
- **AND** the guidance does not recommend a user-scope uninstall merely because the copy is shadowed

#### Scenario: Local test bootstrap evicts an imported user module

- **GIVEN** a test process imported a bundled module from the user-scoped source path
- **WHEN** the local bundle source bootstrap realigns the test process to repository sources
- **THEN** it removes the loaded module from in-memory import state or enforces an equivalent before-import guarantee that prevents reuse of the cached user-scoped module
- **AND** it does not delete or uninstall the user-scoped module files
