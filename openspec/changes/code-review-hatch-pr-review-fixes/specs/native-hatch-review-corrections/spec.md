## ADDED Requirements

### Requirement: Directory alias retargeting invalidates in-project provenance
Project input and source fingerprints SHALL record nonignored directory symlink bindings without following directory links. Retargeting an alias between in-project configuration directories SHALL invalidate preparation before command execution. Relevant physical target configuration content SHALL remain fingerprinted. Existing traversal exclusions and error behavior SHALL remain effective.

#### Scenario: Retarget an in-project test configuration alias
- **GIVEN** two project directories containing different pytest configuration and a directory alias selecting one
- **WHEN** the alias is retargeted after preparation
- **THEN** both identities change and the next command returns a stale-configuration failure before executing

#### Scenario: Change configuration at the selected physical target
- **WHEN** a relevant configuration file changes in the physically traversed target directory
- **THEN** the alias does not hide that input change

### Requirement: Migration scope survives normal squash integration
The default native scope check SHALL use a committed reviewed baseline that remains available in a final-tree-only Git checkout. It SHALL preserve classified additions, content edits, type and executable-mode changes as nonaccepting, allow unchanged/native work and retirement deletions, and retain policy fingerprint binding. Explicit historical comparison SHALL continue to validate revision arguments safely and fail when requested history is unavailable. The old freeze revision SHALL remain audit metadata rather than a default runtime dependency.

#### Scenario: Verify a squash-only checkout
- **GIVEN** a new Git repository containing only the final committed tree and no feature-branch history
- **WHEN** mandatory native scope checking runs
- **THEN** unchanged/native/deletion states pass while classified edits, additions and mode changes fail

#### Scenario: Retain policy and revision protections
- **WHEN** a policy-only mutation weakens the reviewed baseline or a historical argument is option-shaped
- **THEN** checking fails without interpreting revision text as a Git option

#### Scenario: Preserve Git checkout and index semantics
- **WHEN** Git materializes unchanged classified files with CRLF line endings
- **THEN** their cleaned Git identities remain accepted
- **WHEN** a classified executable mode is changed in the index while filesystem mode tracking is disabled
- **THEN** the staged mode change remains rejected
