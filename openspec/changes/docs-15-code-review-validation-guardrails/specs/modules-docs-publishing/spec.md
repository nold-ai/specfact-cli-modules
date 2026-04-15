# ADDED Requirements

## Requirement: Docs publishing SHALL validate generated-site readiness before deploy

The docs publishing workflow SHALL run docs dependency installation, Jekyll build, and generated-site validation before uploading or deploying the Pages artifact.

### Scenario: Dependency install failure blocks Pages artifact

- **WHEN** `bundle install` fails for the docs site
- **THEN** the docs publishing workflow fails before `jekyll build`
- **AND** no Pages artifact is uploaded from that run

### Scenario: Generated site contains broken internal link

- **WHEN** the generated `_site` HTML contains an internal `modules.specfact.io` link whose route is not present in the generated site or redirect set
- **THEN** generated-site validation reports the broken route
- **AND** the docs publishing workflow fails before deployment

## Requirement: Docs review CI SHALL run the same deterministic docs validators as local checks

The docs review workflow SHALL run the deterministic docs validators used by local pre-commit, plus the docs unit tests, so PR and local validation enforce the same defect categories.

### Scenario: Docs-only pull request has broken published link

- **WHEN** a pull request changes only Markdown files under `docs/`
- **THEN** the docs review workflow runs published-route link validation
- **AND** the workflow fails when the changed docs introduce a broken published-route link
