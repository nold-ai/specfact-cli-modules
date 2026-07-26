# module-command-overview Specification

## Purpose
This specification defines deterministic module command overview artifacts and
the docs validation checks that keep published module command references aligned
with the actual command tree.
## Requirements
### Requirement: Modules Publish Generated Command Overview Artifacts

The modules repository SHALL generate deterministic command overview artifacts
from the actual module command tree and authoritative official-module manifest
and registry inventory.

#### Scenario: Module command overview artifacts are generated

- **GIVEN** the module command overview generator runs in the modules repository
- **WHEN** it writes artifacts
- **THEN** it produces `llms.txt`, `docs/reference/commands.generated.md`, and
  `docs/reference/commands.generated.json`
- **AND** every command record includes command path, owning repo, owning module
  package, install prerequisite, short help, arguments/options, subcommands,
  source import path when known, and hidden/deprecated status
- **AND** generated output is stable for the same source tree.

#### Scenario: Official inventory is not represented by command mounts

- **GIVEN** an official package or grouped root in manifests and the registry is
  missing, renamed, or remapped relative to the command-mount inventory
- **WHEN** command overview generation or freshness validation runs
- **THEN** it exits non-zero and identifies the unrepresented or inconsistent
  official record
- **AND** it does not certify unchanged generated artifacts as current.

#### Scenario: README links generated overview

- **GIVEN** a user or AI agent opens the modules repository README
- **WHEN** they look for command usage
- **THEN** the README links to the generated module command overview artifact.

#### Scenario: Stale generated artifacts fail checks

- **GIVEN** any path under `packages/**` or `registry/**` changes, or command
  overview, prompt, docs, or command-validation tooling changes
- **WHEN** the command overview freshness check runs
- **THEN** local pre-commit regenerates and stages all generated artifacts after
  rejecting relevant unstaged inputs
- **AND** CI performs a read-only check and fails if the artifacts are stale
- **AND** the failure reports the command needed to regenerate them.

