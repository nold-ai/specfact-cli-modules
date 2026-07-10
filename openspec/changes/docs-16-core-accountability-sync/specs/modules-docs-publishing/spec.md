## MODIFIED Requirements

### Requirement: Docs review CI SHALL run the same deterministic docs validators as local checks

The Docs Review workflow SHALL run the deterministic validators used by local
pre-commit, including generated command-overview freshness, command-contract
validation, applicable prompt-command validation, and fail-closed core
documentation accountability, plus docs unit tests.

#### Scenario: Module-only pull request validates core accountability

- **WHEN** a pull request changes module manifests, registry data, package
  source/resources/docs, generated artifacts, validation tooling, dependency
  configuration, or Docs Review workflow inputs
- **THEN** Docs Review runs generated-artifact and core-accountability checks
- **AND** the workflow fails when the paired core catalogue or ownership
  handoff is stale
- **AND** it does not report a passing docs review without those checks.
