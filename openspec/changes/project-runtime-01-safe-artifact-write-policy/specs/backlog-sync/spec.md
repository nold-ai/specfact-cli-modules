## ADDED Requirements

### Requirement: Backlog sync local export paths SHALL avoid silent overwrite
Any `specfact backlog sync` local export or artifact materialization path SHALL avoid silent overwrites of existing user-project artifacts.

#### Scenario: Existing export target produces conflict or safe merge
- **WHEN** backlog sync would write to a local artifact path that already exists
- **THEN** the command SHALL use the runtime safe-write contract to merge, skip, or require explicit replacement
- **AND** SHALL surface the chosen behavior in command output
