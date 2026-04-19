## ADDED Requirements

### Requirement: Security bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-security` that exposes the `security` command and declares truthful bundle dependencies, pip dependencies, and `core_compatibility` for the paired core security findings contract.

#### Scenario: Bundle manifest is loaded

- **WHEN** SpecFact reads installed module manifests
- **THEN** the security bundle is discoverable as an official package with the `security` command and valid compatibility metadata

### Requirement: Scanner adapters normalize into the shared findings model

The bundle SHALL translate SAST, SCA, SBOM, and secret-scan outputs into the paired core security finding and report contracts before results reach reporting, evidence, or policy-mode handling.

#### Scenario: Multiple scanner classes produce results

- **WHEN** the bundle runs configured SAST, dependency, SBOM, and secret scanners
- **THEN** it emits one normalized findings stream that preserves category-specific metadata while using the shared core schema

### Requirement: Policy modes influence security execution

The bundle SHALL honor advisory, mixed, and hard security enforcement modes from shared policy/profile configuration when deciding exit behavior and user-facing report status.

#### Scenario: Hard mode receives a blocking finding

- **WHEN** a scan in hard mode returns a finding that the paired core policy classifies as blocking
- **THEN** the bundle surfaces the failure with the normalized report contract and a non-success command outcome
