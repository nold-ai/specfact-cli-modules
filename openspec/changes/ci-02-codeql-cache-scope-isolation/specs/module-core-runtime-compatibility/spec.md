## ADDED Requirements

### Requirement: Modules Declare Evidence-Backed Core Compatibility Ranges

A module release SHALL declare its earliest supported core version as an
inclusive lower bound and SHALL omit an upper bound unless a known breaking
core version requires one.

#### Scenario: Minimum supported core is admitted

- **GIVEN** `specfact-code-review` requires core 0.55.1 or later
- **WHEN** its compatibility metadata is evaluated
- **THEN** core 0.55.1 is admitted
- **AND** core 0.55.0 is rejected.

#### Scenario: Compatible later core is admitted without module modification

- **GIVEN** no breaking upper core version is known
- **WHEN** the module is installed by a later core version
- **THEN** the manifest range admits that core
- **AND** no exact-version or upper-bound constraint requires a module release
  solely because core received a compatible update.

#### Scenario: CI distinguishes minimum proof from current compatibility

- **GIVEN** the lower compatibility boundary is core 0.55.1
- **WHEN** pull-request validation runs
- **THEN** an immutable tag, commit, and tree smoke validates core 0.55.1
- **AND** the paired-core quality job validates runtime installation against
  the current compatible core.

#### Scenario: A breaking upper version is evidence-backed

- **GIVEN** a later core version is demonstrably incompatible
- **WHEN** module compatibility metadata is revised
- **THEN** a maximum version may be added with evidence for that incompatibility
- **AND** the maximum is not inferred from the highest version currently tested.

### Requirement: Compatibility Corrections Supersede Release-Snapshot Admission Rules

When an earlier change records an exact core identity as release-snapshot
evidence, a later compatibility correction SHALL govern runtime admission while
preserving that immutable identity only as historical and minimum-version proof.

#### Scenario: C14 exact-only wording remains historical evidence

- **GIVEN** C14 release 0.49.59 recorded exact core 0.55.1 admission
- **WHEN** `specfact-code-review` 0.49.60 declares `>=0.55.1`
- **THEN** the minimum-only range governs current and future runtime admission
- **AND** C14 tag, commit, tree, checkpoint, and selector identities remain
  immutable evidence for the 0.55.1 floor
- **AND** archiving C14 later SHALL NOT reintroduce exact-only compatibility as
  current policy; its archive must retain or be followed by this supersession.
