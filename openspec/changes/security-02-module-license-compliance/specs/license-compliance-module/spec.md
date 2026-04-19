## ADDED Requirements

### Requirement: License compliance bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-license-compliance` that exposes the `license` command and declares truthful bundle dependencies, pip dependencies, and `core_compatibility` for the shared core findings model.

#### Scenario: Bundle manifest is loaded

- **WHEN** SpecFact reads installed module manifests
- **THEN** the license-compliance bundle is discoverable as an official package with the `license` command and valid compatibility metadata

### Requirement: SPDX and SBOM evaluation uses the shared findings contract

The bundle SHALL ingest normalized SBOM/license records and emit allow, deny, or exception findings through the paired core findings/report contracts instead of a bundle-local reporting schema.

#### Scenario: A denied license is detected

- **WHEN** the bundle evaluates SBOM records against configured policy and encounters a denied SPDX identifier
- **THEN** it emits a normalized license finding with remediation guidance and a policy-aligned severity

### Requirement: Policy modes control license command outcomes

The bundle SHALL honor advisory, mixed, and hard policy modes when determining command status and user-facing report outcomes for license findings.

#### Scenario: Advisory mode encounters a denied license

- **WHEN** policy mode is advisory and evaluation returns a denied license
- **THEN** the bundle reports the finding without converting the overall command outcome into a blocking failure
