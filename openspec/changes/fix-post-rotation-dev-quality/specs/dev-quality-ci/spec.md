## ADDED Requirements

### Requirement: Use the reviewed tool and fixture for dev quality checks

The quality workflow SHALL use Ruff 0.16.0, the version locked by the paired core. Runtime discovery smoke SHALL use the module commit in the paired core runtime smoke lock from the official modules repository. The existing verifier SHALL check the fixture identity and frozen archives before running any launcher.

#### Scenario: Run quality checks after a modules change

- **WHEN** the quality workflow runs after the modules checkout changes
- **THEN** lint uses the pinned tool with the repository's full lint rules
- **AND** runtime smoke uses the separately checked-out fixture with the existing launcher coverage.
