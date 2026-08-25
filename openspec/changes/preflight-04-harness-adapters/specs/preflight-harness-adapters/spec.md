## ADDED Requirements

### Requirement: Shared adapter identity contract

Every harness adapter SHALL declare the exact signed SpecFact module identity, canonical workflow identity, supported harness versions, native invocation mapping, installed asset inventory, and upgrade/uninstall rules.

#### Scenario: Adapter targets an untested harness version

- **GIVEN** the detected harness version is outside the adapter's proven compatibility range
- **WHEN** installation or upgrade is requested
- **THEN** the adapter stops with a compatibility diagnostic
- **AND** it does not install a best-effort or silently translated workflow.

### Requirement: Validator logic remains centralized

Adapters SHALL invoke the released SpecFact preflight CLI and consume its structured result without implementing readiness validators or recomputing outcomes.

#### Scenario: Harness renders a blocked result

- **GIVEN** the SpecFact CLI returns a blocked result with finding identities
- **WHEN** a Codex, ECC, or hatch3r adapter presents it
- **THEN** the adapter preserves the readiness, finding identities, approval state, and assurance limits
- **AND** no prompt-local rule can convert the result to ready.

### Requirement: Codex plugin adapter

The Codex adapter SHALL expose the canonical preflight workflow through the supported Codex skill/plugin surface and SHALL reference the installed CLI identity.

#### Scenario: Codex user invokes preflight

- **GIVEN** the compatible plugin and signed module are installed
- **WHEN** the user invokes the Codex-native `specfact-preflight` workflow for a change
- **THEN** the canonical workflow runs with the selected change ID
- **AND** the plugin contains no duplicate Python validator implementation.

### Requirement: ECC skills-first adapter

The ECC adapter SHALL install the canonical workflow as a skill and SHALL add a command shim only when the supported ECC target requires it.

#### Scenario: ECC target supports direct skill invocation

- **GIVEN** the target ECC version exposes the installed skill directly
- **WHEN** the adapter installs
- **THEN** it does not add a redundant command shim
- **AND** generated instructions reference the native skill invocation.

### Requirement: hatch3r inventory-driven adapter

The hatch3r integration SHALL register the canonical workflow in the supported package inventory/generation model and SHALL generate only adapters supported by the selected hatch3r release.

#### Scenario: Removed hatch3r adapter is requested

- **GIVEN** the selected hatch3r release no longer supports a platform adapter
- **WHEN** SpecFact integration is generated
- **THEN** the removed adapter is not recreated
- **AND** the user receives the supported target list from current hatch3r metadata.

### Requirement: Idempotent install and safe uninstall

Adapter installation and upgrade SHALL be idempotent, and uninstall SHALL remove only recorded adapter-owned assets whose identity still matches the install record.

#### Scenario: User modified an installed instruction file

- **GIVEN** an adapter-owned file differs from its recorded installed digest
- **WHEN** upgrade or uninstall is requested
- **THEN** the adapter reports drift and preserves the file unless the user explicitly resolves it
- **AND** unrelated harness assets are never removed.

### Requirement: Cross-adapter semantic parity

Codex, ECC, and hatch3r adapters SHALL preserve the canonical workflow phases, CLI delegation, approval points, stop states, and assurance-limit language despite different native file formats.

#### Scenario: Adapter contract matrix runs

- **GIVEN** fixtures for all supported adapter/version pairs
- **WHEN** the parity matrix evaluates generated assets and invocations
- **THEN** every adapter maps to the same canonical workflow identity and semantics
- **AND** platform-specific syntax differences are explicitly recorded rather than treated as workflow differences.
