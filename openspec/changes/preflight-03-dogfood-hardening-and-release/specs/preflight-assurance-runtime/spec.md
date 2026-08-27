## MODIFIED Requirements

### Requirement: Deterministic pre-implementation loop

The stable module SHALL execute a stateful pre-implementation loop that discovers a change, captures exact inputs, runs required validators, presents findings, accepts only user-authorized refinement, reruns after changes, records explicit approval, and verifies the resulting seal before implementation. It SHALL retain regression evidence for every accepted dogfood defect that affected snapshotting, validation, review, refinement, approval, sealing, or verification.

#### Scenario: Ready change is approved and sealed

- **GIVEN** all required inputs are identified and every required validator returns a determinate non-blocking result
- **WHEN** the user explicitly approves the displayed contract and validation summary
- **THEN** the runtime records an approval seal bound to the exact reviewed identities
- **AND** a subsequent verification step succeeds only while those identities remain current.

#### Scenario: Blocking or unknown result stops the loop

- **GIVEN** a required validator reports a blocking finding, does not complete, or cannot identify an authoritative source
- **WHEN** readiness is aggregated
- **THEN** the runtime reports `BLOCKED` or `UNKNOWN`
- **AND** it does not offer approval or state that implementation may begin.

#### Scenario: Hardened loop processes the C14 corpus

- **GIVEN** the exact accepted C14 dogfood corpus and a fresh supported environment
- **WHEN** the stable candidate executes the loop
- **THEN** all required validators complete with the expected findings and readiness states
- **AND** no previously accepted defect regresses.

### Requirement: Canonical skill and slash-command contract

The stable module SHALL bundle and publish one versioned canonical `specfact-preflight` workflow that invokes the deterministic CLI, can be exported to harness-native invocation forms, has tested CLI delegation, and contains no external harness-specific packaging. The official installation or preflight path SHALL load the workflow from the signed installation and verify its workflow version/digest and delegated CLI identity as one release-bound tuple.

#### Scenario: Harness invokes bundled workflow

- **GIVEN** a compatible installer exposes the bundled workflow as `/specfact-preflight`, `$specfact-preflight`, or another native alias
- **WHEN** a user selects an OpenSpec change
- **THEN** the workflow invokes the supported preflight CLI and consumes structured output
- **AND** it does not duplicate validator logic in the prompt.

#### Scenario: Workflow encounters ambiguous refinement

- **GIVEN** findings require a material scope or design choice
- **WHEN** the skill presents possible refinements
- **THEN** it pauses for user direction
- **AND** it does not silently change or approve the source artifacts.

#### Scenario: Stable workflow asset is loaded

- **GIVEN** the signed module is installed through the official path
- **WHEN** a compatible generic installer discovers the workflow asset
- **THEN** it receives the canonical workflow identity and supported invocation contract
- **AND** the delegated CLI identity matches the signed release identity
- **AND** adapter-specific files are not required to execute the underlying CLI.
