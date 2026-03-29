# Module Release History Docs

## ADDED Requirements

### Requirement: Modules docs overview SHALL show recent published module releases

The modules docs overview SHALL present recent published module versions together with shipped features and improvements so users can quickly understand what each module has released.

#### Scenario: Overview shows recent release details

- **GIVEN** structured release-history entries exist for official modules
- **WHEN** the modules docs site is built
- **THEN** the overview renders recent module versions with user-friendly shipped features and improvements
- **AND** the rendering uses repository data at build time without runtime network fetches

#### Scenario: Sparse history degrades gracefully

- **GIVEN** a module has only partial or newly initialized release-history data
- **WHEN** the docs overview renders that module
- **THEN** the page still shows the published version context available
- **AND** it does not break the rest of the overview

### Requirement: OpenSpec project rules SHALL describe release-history update expectations

The project OpenSpec configuration SHALL guide future release-oriented changes to include release-history extraction or update steps when they affect published modules or docs that summarize them.

#### Scenario: Release-oriented change references release-history expectations

- **GIVEN** a future change modifies an official module payload or publish workflow
- **WHEN** proposal artifacts are created under the project OpenSpec rules
- **THEN** the rules call out release-history update expectations where applicable
- **AND** docs-sync changes can rely on that canonical release-history source

#### Scenario: Release-note style guidance is available to AI copilot

- **GIVEN** a future release-oriented change uses AI copilot to help draft module release or patch notes
- **WHEN** project OpenSpec rules are consulted
- **THEN** they instruct the AI to keep notes user-focused and scope-explicit
- **AND** they discourage technical bla bla or generic filler text
