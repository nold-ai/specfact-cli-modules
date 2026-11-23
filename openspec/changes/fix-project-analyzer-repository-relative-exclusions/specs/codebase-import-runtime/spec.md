## ADDED Requirements

### Requirement: Project analyzer uses repository-relative directory exclusions

The project analyzer SHALL match its existing directory exclusions against complete directory names inside the selected repository. Repository and ancestor names and partial source path matches SHALL NOT exclude production files. Existing test-file exclusions SHALL remain in effect.

#### Scenario: Production source under a misleading path is analyzed

- **WHEN** a repository, ancestor, or production path contains a fragment such as `env`, `build`, or `dist`
- **THEN** the project analyzer SHALL still include that production source when no actual exclusion applies

#### Scenario: A matching child directory is excluded

- **WHEN** a production source resides under an existing excluded directory such as `build` inside the repository
- **THEN** the project analyzer SHALL exclude the source
