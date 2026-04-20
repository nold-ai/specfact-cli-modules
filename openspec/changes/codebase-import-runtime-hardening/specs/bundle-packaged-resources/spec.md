## MODIFIED Requirements

### Requirement: Official bundles SHALL ship module-owned resource payloads
Each official bundle package SHALL include the prompt templates and other non-code resources that are owned by that bundle's workflows or commands. Bundle-owned resources SHALL not depend on fallback storage under the core CLI repository.

#### Scenario: Project runtime generators ship required Jinja2 templates
- **WHEN** the project bundle is built, installed, or imported from an editable checkout
- **THEN** every generator template referenced by the project runtime exists under the bundle-owned packaged resource paths
- **AND** runtime template lookup resolves those packaged templates without depending on files from the core CLI repository

#### Scenario: Missing generator templates fail bundle payload validation
- **WHEN** a required project runtime template such as `protocol.yaml.j2` or `github-action.yml.j2` is absent from the package payload
- **THEN** bundle resource validation SHALL fail before release
- **AND** the failure message SHALL name the missing template path so the packaging defect can be corrected before publish
