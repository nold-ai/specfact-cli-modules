## ADDED Requirements

### Requirement: Bundle prompt command references SHALL match mounted CLI contracts

The modules repository SHALL validate command paths and option names embedded in bundle-owned prompt resources against the mounted SpecFact CLI command tree discoverable from the current checkout.

#### Scenario: Valid prompt command example passes

- **GIVEN** a bundle prompt references an implemented command such as `specfact code repro --repo .`
- **WHEN** prompt command validation runs
- **THEN** the command path resolves through the mounted CLI command tree
- **AND** referenced options are accepted by that command or by an ancestor command context

#### Scenario: Invalid prompt command path fails

- **GIVEN** a bundle prompt references a stale command such as `specfact repro --repo .`
- **WHEN** prompt command validation runs
- **THEN** the validator reports the prompt path and line number
- **AND** the validation command exits non-zero

#### Scenario: Invalid prompt option fails

- **GIVEN** a bundle prompt references an option that is not accepted by the resolved command path
- **WHEN** prompt command validation runs
- **THEN** the validator reports the stale option, prompt path, and line number
- **AND** the validation command exits non-zero

### Requirement: Prompt guidance SHALL self-check CLI reality

Bundle-owned prompts SHALL tell AI IDE assistants that prompt text is operational guidance and that current CLI help or validation output is authoritative when prompt instructions disagree with the installed CLI.

#### Scenario: Prompt contains CLI reality check guidance

- **GIVEN** a shipped bundle prompt contains executable SpecFact command guidance
- **WHEN** prompt command validation inspects that prompt
- **THEN** the prompt includes a CLI reality-check instruction
- **AND** the prompt tells the assistant to prefer current CLI help over stale prompt prose

#### Scenario: Broken prompt instruction gives self-healing behavior

- **GIVEN** an assistant using a prompt finds that a referenced command or option is unavailable
- **WHEN** the prompt includes self-healing guidance
- **THEN** the assistant is instructed to inspect the nearest valid `--help` output
- **AND** continue only with a corrected command or ask the user when no safe correction is clear

### Requirement: Prompt validation SHALL run in local and CI gates

Prompt command validation SHALL be available as a Hatch command and SHALL run automatically in local pre-commit and Markdown/resource-triggered CI when bundle prompt resources or validation tooling change.

#### Scenario: Hatch command exposes prompt validation

- **WHEN** a contributor runs `hatch run validate-prompt-commands`
- **THEN** the bundle prompt validation script runs
- **AND** exits non-zero on any blocking prompt command finding

#### Scenario: Pre-commit validates staged prompt edits before safe-change skipping

- **GIVEN** a staged edit changes `packages/specfact-project/resources/prompts/specfact.02-plan.md`
- **WHEN** `scripts/pre-commit-quality-checks.sh block2` runs
- **THEN** prompt command validation runs before the script decides whether Block 2 can be skipped as a safe change

#### Scenario: CI validates prompt edits

- **GIVEN** a pull request changes a bundle prompt Markdown file
- **WHEN** the docs review workflow runs
- **THEN** prompt command validation runs with logs
- **AND** stale command references fail the workflow
