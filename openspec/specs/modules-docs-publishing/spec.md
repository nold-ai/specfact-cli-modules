# modules-docs-publishing Specification

## Purpose
TBD - created by archiving change docs-01-modules-docs-canonical-site. Update Purpose after archive.
## Requirements
### Requirement: Modules docs site is the canonical home for official bundle documentation

The modules documentation site SHALL present itself as the canonical published home for official bundle and module-specific deep documentation.

#### Scenario: Reader opens modules landing page

- **WHEN** a reader opens the modules docs landing page
- **THEN** the page states that official bundle and module-specific deep guidance is owned by `specfact-cli-modules`
- **AND** the page does not describe the GitHub Pages project-path URL as the long-term canonical public identity.

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

