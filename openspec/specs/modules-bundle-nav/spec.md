# modules-bundle-nav Specification

## Purpose
TBD - created by archiving change docs-06-modules-site-ia-restructure. Update Purpose after archive.
## Requirements
### Requirement: Modules docs sidebar SHALL provide per-bundle collapsible navigation

The modules docs sidebar SHALL group all docs for each official bundle under a collapsible section and SHALL display a consistent top-level section order.

#### Scenario: Sidebar shows 7 sections in correct order

- **GIVEN** the modules docs site is built with Jekyll
- **WHEN** a user visits any page on modules.specfact.io
- **THEN** the sidebar displays sections: Getting Started, Bundles, Workflows, Integrations, Team & Enterprise, Authoring, Reference

#### Scenario: Bundles section has collapsible per-bundle groups

- **GIVEN** the sidebar Bundles section
- **WHEN** a user expands a bundle (e.g., Backlog)
- **THEN** they see all docs for that bundle: Overview, Ceremonies, Refinement, Delta Commands, etc.
- **AND** each bundle group is independently collapsible

#### Scenario: Moved files redirect to new locations

- **GIVEN** a file was moved from guides/ to bundles/
- **WHEN** a user visits the old URL
- **THEN** they are redirected to the new URL via jekyll-redirect-from

