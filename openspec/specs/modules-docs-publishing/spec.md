# modules-docs-publishing Specification

## Purpose
This specification governs the modules documentation publishing contract,
including deterministic site inputs, generated navigation, and published-link
validation for changed docs.

## Requirements
### Requirement: Modules docs site is the canonical home for official bundle documentation

The modules documentation site SHALL present itself as the canonical published home for official bundle and module-specific deep documentation, and its command examples SHALL match the currently mounted CLI surface shipped with the official modules.

#### Scenario: Reader follows a command example from the modules docs

- **WHEN** a reader copies a command example from the modules docs reference or installation pages
- **THEN** the example uses a command path that is currently mounted in `specfact --help`
- **AND** the example does not rely on removed top-level shims such as flat `sync`, `repro`, `validate`, or `enforce` command groups when the mounted path is nested under another group
- **AND** official bundle install examples use the current published module ids from `specfact-cli-modules`

### Requirement: Modules docs expose shared cross-site navigation

The modules documentation site SHALL expose shared top-level navigation labels that align with the canonical docs information architecture.

#### Scenario: Reader uses top navigation

- **WHEN** a reader opens the modules docs site
- **THEN** the top navigation includes `Docs Home`, `Core CLI`, and `Modules`
- **AND** the links guide the reader to the canonical docs entry point and core docs section without ambiguity.

### Requirement: Modules docs remain independently publishable

The modules documentation site SHALL support independent publishing and deployment without requiring a combined docs build with `specfact-cli`.

#### Scenario: Module-only docs change is published

- **WHEN** a change affects only `specfact-cli-modules/docs`
- **THEN** the modules docs build and publication workflow can ship the change without rebuilding the core docs site
- **AND** the site metadata and navigation remain valid for the public docs topology.

### Requirement: Published URL contract is documented and redirects preserve legacy paths

The modules documentation site SHALL maintain a published reference page that explains ownership boundaries and permalink rules relative to `docs.specfact.io`, and SHALL use `redirect_from` so that prior public URLs under `/guides/<basename>/` continue to resolve when the canonical permalink moves to a non-`/guides/` path or to bundle/integration paths.

#### Scenario: Contributor looks up cross-site linking rules

- **WHEN** a contributor needs to link from core docs to modules docs or change a `permalink`
- **THEN** the reference page at `/reference/documentation-url-contract/` on `modules.specfact.io` describes repository ownership, default permalink behavior, and redirect expectations
- **AND** pages that publish outside `/guides/<basename>/` include `redirect_from` for `/guides/<basename>/` when that path could have been used historically

#### Scenario: IA-moved guide keeps old URL working

- **WHEN** a guide is moved under `bundles/`, `integrations/`, or `authoring/` with a new canonical `permalink`
- **THEN** the page includes `jekyll-redirect-from` entries for the previous modules URL (as required by the IA restructure change)

### Requirement: Docs publishing SHALL validate generated-site readiness before deploy

The docs publishing workflow SHALL run docs dependency installation, Jekyll build, and generated-site validation before uploading or deploying the Pages artifact.

#### Scenario: Dependency install failure blocks Pages artifact

- **WHEN** `bundle install` fails for the docs site
- **THEN** the docs publishing workflow fails before `jekyll build`
- **AND** no Pages artifact is uploaded from that run

#### Scenario: Generated site contains broken internal link

- **WHEN** the generated `_site` HTML contains an internal `modules.specfact.io` link whose route is not present in the generated site or redirect set
- **THEN** generated-site validation reports the broken route
- **AND** the docs publishing workflow fails before deployment

### Requirement: Docs review CI SHALL run the same deterministic docs validators as local checks

The docs review workflow SHALL run the deterministic docs validators used by local pre-commit, plus the docs unit tests, so PR and local validation enforce the same defect categories.

#### Scenario: Docs-only pull request has broken published link

- **WHEN** a pull request changes only Markdown files under `docs/`
- **THEN** the docs review workflow runs `published-link` validation
- **AND** the workflow fails when the changed docs introduce a broken `published-link`
