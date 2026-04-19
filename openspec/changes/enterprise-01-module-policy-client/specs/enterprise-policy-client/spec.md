## ADDED Requirements

### Requirement: Enterprise policy bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-enterprise-policy` that exposes enterprise policy sync commands and declares truthful bundle dependencies, pip dependencies, and `core_compatibility` for the paired core enterprise policy contracts.

#### Scenario: Bundle manifest is loaded

- **WHEN** SpecFact reads installed module manifests
- **THEN** the enterprise policy bundle is discoverable as an official package with sync/status commands and valid compatibility metadata

### Requirement: Policy payloads are verified before use

The bundle SHALL verify payload integrity and freshness metadata before cached enterprise policy layers influence local resolution behavior.

#### Scenario: A signed policy payload is fetched

- **WHEN** the bundle downloads a policy payload from a configured enterprise endpoint
- **THEN** it validates the payload metadata before storing it in the local cache or marking the policy layer as active

### Requirement: Missing enterprise configuration is a no-op state

The bundle SHALL surface a clear no-op status when no enterprise endpoint is configured and SHALL not modify local policy resolution in that state.

#### Scenario: No enterprise endpoint is configured

- **WHEN** a user runs the enterprise policy status command without enterprise configuration
- **THEN** the bundle reports that enterprise policy sync is inactive and leaves local resolution behavior unchanged
