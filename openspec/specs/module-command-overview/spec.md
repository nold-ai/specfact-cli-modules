# module-command-overview Specification

## Purpose
This specification defines deterministic module command overview artifacts and
the docs validation checks that keep published module command references aligned
with the actual command tree.

## Requirements
### Requirement: Modules Publish Generated Command Overview Artifacts

The modules repository SHALL generate deterministic command overview artifacts from the actual module command tree.

#### Scenario: Module command overview artifacts are generated

- **GIVEN** the module command overview generator runs in the modules repository
- **WHEN** it writes artifacts
- **THEN** it produces `llms.txt`, `docs/reference/commands.generated.md`, and `docs/reference/commands.generated.json`
- **AND** every command record includes command path, owning repo, owning module package, install prerequisite, short help, arguments/options, subcommands, source import path when known, and hidden/deprecated status
- **AND** generated output is stable for the same source tree.

#### Scenario: README links generated overview

- **GIVEN** a user or AI agent opens the modules repository README
- **WHEN** they look for command usage
- **THEN** the README links to the generated module command overview artifact.

#### Scenario: Stale generated artifacts fail checks

- **GIVEN** module command source, module manifests, prompt resources, docs, or command validation scripts change
- **WHEN** the command overview freshness check runs
- **THEN** it fails if generated artifacts are stale
- **AND** it reports the command needed to regenerate them.
