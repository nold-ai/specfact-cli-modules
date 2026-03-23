# Capability: modules-bundle-nav

Modules docs sidebar provides per-bundle collapsible navigation grouping all docs for each official bundle.

## Scenarios

### Scenario: Sidebar shows 7 sections in correct order

Given the modules docs site is built with Jekyll
When a user visits any page on modules.specfact.io
Then the sidebar displays sections: Getting Started, Bundles, Workflows, Integrations, Team & Enterprise, Authoring, Reference

### Scenario: Bundles section has collapsible per-bundle groups

Given the sidebar Bundles section
When a user expands a bundle (e.g., Backlog)
Then they see all docs for that bundle: Overview, Ceremonies, Refinement, Delta Commands, etc.
And each bundle group is independently collapsible

### Scenario: Moved files redirect to new locations

Given a file was moved from guides/ to bundles/
When a user visits the old URL
Then they are redirected to the new URL via jekyll-redirect-from
