# Module Release History Registry

## ADDED Requirements

### Requirement: Official module publishes SHALL persist structured release-history entries

The modules repository SHALL maintain a canonical structured release-history source for official modules, and each newly published module version SHALL add a corresponding release-history entry as part of the publish workflow.

#### Scenario: Publish writes release-history entry

- **GIVEN** an official module version is published through the repository publish workflow
- **WHEN** the workflow updates registry metadata for that published version
- **THEN** it also records a structured release-history entry for that module id and version
- **AND** the entry includes user-facing shipped features and/or improvements for that release

### Requirement: AI-assisted module release notes SHALL stay user-focused

AI-assisted module release-note generation SHALL produce clear user-facing summaries of shipped scope and SHALL avoid low-signal technical filler.

#### Scenario: Publish-time release note is user-facing

- **GIVEN** a module publish includes AI-assisted release-note drafting
- **WHEN** the release-history entry is generated
- **THEN** the resulting summary explains what shipped in user-facing language
- **AND** it prioritizes concrete features, improvements, or fixes
- **AND** it avoids unnecessary implementation detail that does not help users understand the release

#### Scenario: Canonical history is separate from lean registry index

- **GIVEN** the repository maintains `registry/index.json` for install/search metadata
- **WHEN** release-history metadata is added
- **THEN** the richer per-version history is stored in a separate canonical source
- **AND** `registry/index.json` remains focused on latest install/search metadata

### Requirement: Existing published module versions SHALL be backfilled through a reviewable extraction flow

The repository SHALL support a one-time backfill process for already-published official module versions so the docs can show useful release history from launch.

#### Scenario: Historical versions produce candidate entries

- **GIVEN** official module versions already listed in `registry/index.json`
- **WHEN** the historical backfill process runs
- **THEN** it produces candidate structured release-history entries for those versions
- **AND** the candidates are presented in a reviewable form before being accepted as canonical
