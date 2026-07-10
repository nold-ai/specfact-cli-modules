## ADDED Requirements

### Requirement: Modules SHALL enforce core documentation accountability from the authoritative checker

The modules repository SHALL invoke the authoritative core
documentation-accountability checker against the current modules checkout. The
modules-side integration SHALL resolve the core checkout from
`SPECFACT_CLI_REPO`, then the matching paired worktree, then the documented
sibling checkout, and SHALL fail closed with setup guidance when none supplies
the required checker. It SHALL NOT duplicate official-module inventory or core
catalogue validation rules.

#### Scenario: Module inventory change exposes stale core documentation

- **GIVEN** a modules manifest or grouped command root changes
- **AND** the paired core catalogue, generated command artifact, or ownership
  handoff remains stale
- **WHEN** the modules documentation-accountability gate runs
- **THEN** the core authoritative checker exits non-zero
- **AND** reports the stale core documentation context.

#### Scenario: Paired core checkout is unavailable

- **GIVEN** `SPECFACT_CLI_REPO`, the paired worktree, and the sibling checkout
  do not provide the core checker
- **WHEN** the modules local gate runs
- **THEN** it exits non-zero with instructions to configure or create a paired
  core checkout
- **AND** it does not skip or substitute a duplicated local checker.

### Requirement: Core accountability SHALL block matching local and PR gates

The same modules-side core-accountability command SHALL run before a docs-only
safe bypass in pre-commit and as a blocking Docs Review workflow step. Docs
Review SHALL use the same-named core branch when available, otherwise the
sanitized `dev` or `main` base fallback, and SHALL fail when the checkout or
checker cannot be resolved.

#### Scenario: Modules PR checks a matching core branch

- **GIVEN** a modules pull-request branch has a same-named branch in the core
  repository
- **WHEN** Docs Review runs
- **THEN** it checks out that core branch
- **AND** core-accountability failures block the workflow.

#### Scenario: Modules PR falls back to the base core branch

- **GIVEN** the same-named core branch does not exist
- **WHEN** Docs Review runs for a `dev` or `main` pull request
- **THEN** it uses the corresponding base branch
- **AND** it fails rather than silently skipping accountability validation.
