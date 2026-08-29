## ADDED Requirements

### Requirement: Shared adapter identity contract

Every harness adapter SHALL declare and verify the exact signed #434 module version, artifact digest, authorized signature/trust-root identity, registry identity, compatible core identity, separately named preflight workflow identity/digest and implementation-check workflow identity/digest, supported harness versions, native invocation mapping, installed asset inventory, and upgrade/uninstall rules. When the released installer owns cryptographic verification, adapters SHALL consume its verified result and SHALL verify the role-specific manifest mappings `preflight workflow identity -> preflight workflow digest` and `implementation-check workflow identity -> implementation-check workflow digest` before installation, upgrade, invocation, or packaging. Presence of both identities and both digests without the correct pairings SHALL NOT satisfy verification.

#### Scenario: Immutable release identity does not match

- **GIVEN** the installed or selected module digest, signature, registry identity, or compatible core identity differs from the adapter descriptor
- **WHEN** installation or upgrade is requested
- **THEN** the adapter rejects the mismatched release identity
- **AND** it does not invoke or package the workflow from that release.

#### Scenario: Signature or installed workflow is invalid or untrusted

- **GIVEN** signature verification fails against the authorized trust root, the verified installer result is absent, either role-specific workflow identity/digest pair is omitted or mismatched, the identities/digests are cross-paired, or either installed workflow digest differs from its corresponding signed manifest mapping
- **WHEN** installation, upgrade, invocation, or packaging is requested
- **THEN** the adapter fails closed before the operation
- **AND** it does not treat descriptor text alone as verification.

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

### Requirement: hatch3r distribution prerequisite

The hatch3r integration SHALL ship only through a distribution/extension surface contained and documented by the selected hatch3r release. A separately accepted upstream hatch3r contribution SHALL qualify only after it is merged, included in that release, and documented there. Until that released and documented surface exists, hatch3r packaging SHALL remain blocked and SHALL NOT write internal inventory data or depend on private package layout.

#### Scenario: Selected hatch3r release has no supported extension surface

- **GIVEN** the selected hatch3r release documents no third-party pack, inventory-registration, or equivalent supported distribution API
- **WHEN** SpecFact adapter packaging is requested
- **THEN** hatch3r packaging is blocked pending a selected release that contains and documents the supported prerequisite
- **AND** no internal inventory or private package content is modified.

#### Scenario: Accepted upstream contribution is not yet released

- **GIVEN** an upstream contribution adding an extension surface has been accepted or merged
- **AND** the selected hatch3r release does not yet contain and document that surface
- **WHEN** SpecFact adapter packaging is requested
- **THEN** hatch3r packaging remains blocked.

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
- **THEN** every adapter maps to the same signed #434 module identity plus the same preflight and implementation-check workflow identities/digests and semantics
- **AND** platform-specific syntax differences are explicitly recorded rather than treated as workflow differences.
