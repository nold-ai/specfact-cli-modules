# speckit-change-proposal-bridge Specification

## Purpose
TBD - created by archiving change speckit-03-change-proposal-bridge. Update Purpose after archive.
## Requirements
### Requirement: Convert spec-kit feature folder to OpenSpec change proposal

The system SHALL convert a spec-kit feature folder into a complete OpenSpec change proposal with all required artifacts (proposal.md, design.md, specs/, tasks.md).

#### Scenario: Convert complete spec-kit feature

- **GIVEN** a spec-kit feature folder at `specs/{feature}/` containing `spec.md`, `plan.md`, and `tasks.md`
- **WHEN** `SpecKitConverter.convert_to_change_proposal(feature_path, change_name)` is called
- **THEN** the converter creates an OpenSpec change directory at `openspec/changes/{change_name}/`
- **AND** generates `proposal.md` with Why section extracted from spec.md narrative and What Changes from requirements
- **AND** generates `design.md` with Context from plan.md technical context and Decisions from plan.md phases
- **AND** generates `specs/{capability}/spec.md` with requirements reformatted as Given/When/Then scenarios
- **AND** generates `tasks.md` with checkbox groups mapped from spec-kit task phases

#### Scenario: Convert spec-kit feature with INVEST criteria

- **GIVEN** a spec-kit feature with user stories containing INVEST criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable)
- **WHEN** the feature is converted to an OpenSpec change proposal
- **THEN** INVEST criteria are preserved as structured comments in the generated spec scenarios
- **AND** each user story maps to one or more Given/When/Then scenario blocks

#### Scenario: Convert spec-kit feature missing plan.md

- **GIVEN** a spec-kit feature folder with `spec.md` and `tasks.md` but no `plan.md`
- **WHEN** `SpecKitConverter.convert_to_change_proposal(feature_path, change_name)` is called
- **THEN** the converter generates `proposal.md`, `specs/`, and `tasks.md`
- **AND** generates a minimal `design.md` with a placeholder Context section
- **AND** logs a warning that plan.md was not found

### Requirement: Convert OpenSpec change proposal to spec-kit feature folder

The system SHALL convert an OpenSpec change proposal back to spec-kit feature folder format.

#### Scenario: Export change proposal to spec-kit format

- **GIVEN** an OpenSpec change proposal at `openspec/changes/{change_name}/` with all 4 artifacts
- **WHEN** `SpecKitConverter.convert_to_speckit_feature(change_dir, output_dir)` is called
- **THEN** the converter creates a spec-kit feature folder at `{output_dir}/{feature_name}/`
- **AND** generates `spec.md` with user stories extracted from spec scenarios
- **AND** generates `plan.md` with technical context from design.md
- **AND** generates `tasks.md` with checklist items from tasks.md checkbox groups

#### Scenario: Roundtrip preservation

- **GIVEN** a spec-kit feature converted to OpenSpec and then back to spec-kit format
- **WHEN** the roundtrip conversion completes
- **THEN** all user stories from the original spec.md are present in the output spec.md
- **AND** all task items from the original tasks.md are present in the output tasks.md
- **AND** unmappable fields are preserved as annotation comments

### Requirement: Sync bridge change-proposal mode

The system SHALL support a `--mode change-proposal` option on the `specfact sync bridge` command that operates on change proposals rather than plan bundles.

#### Scenario: Sync spec-kit feature as change proposal

- **GIVEN** a spec-kit repository detected by `BridgeProbe`
- **WHEN** `specfact sync bridge --adapter speckit --mode change-proposal --feature {name}` is called
- **THEN** the command converts the specified spec-kit feature to an OpenSpec change proposal
- **AND** writes the change to `openspec/changes/{derived-change-name}/`
- **AND** displays a summary of created artifacts

#### Scenario: Sync all untracked spec-kit features

- **GIVEN** a spec-kit repository with 3 features, 1 already has an OpenSpec change
- **WHEN** `specfact sync bridge --adapter speckit --mode change-proposal --all` is called
- **THEN** the command converts only the 2 untracked features to OpenSpec change proposals
- **AND** skips the feature that already has a corresponding change

