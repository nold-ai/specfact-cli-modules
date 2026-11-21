## ADDED Requirements

### Requirement: Sign only the approved Codebase candidate
The signature workflow SHALL expose a job triggered by the fixed payload file entering protected dev with the existing module-signing approval. It SHALL sign only the fixed Codebase 0.42.1 payload and only with the pinned replacement key. The output SHALL be a verified detached signature. Repository and publication state SHALL require separate operations.

#### Scenario: Sign the reviewed payload after environment approval
- **GIVEN** the reviewed payload and replacement signing key are present on the protected workflow
- **WHEN** the reviewed payload enters protected dev and a maintainer grants the required environment approval
- **THEN** the job verifies the payload and replacement key identities and emits a detached signature that verifies against the tracked public key

#### Scenario: Reject mismatched payload or key
- **GIVEN** the candidate data, configured fingerprint or signing key differs from the reviewed identities
- **WHEN** the signing step runs
- **THEN** it fails without publishing a signature
