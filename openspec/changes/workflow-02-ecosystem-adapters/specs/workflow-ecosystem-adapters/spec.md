## ADDED Requirements

### Requirement: Thin upstream and CI invocation adapters

The modules repository SHALL provide an optional Spec Kit extension using documented pinned upstream extension hooks and a GitHub Actions integration invoking released SpecFact commands. Authoring, clarification and task generation SHALL remain upstream-owned. The integration SHALL verify compatible signed module/core identities and preserve producer exit codes and complete native reports. Hooks SHALL be documented as invocation assistance; protected CI SHALL remain the enforcement boundary. The first certified execution path SHALL use structured pytest runner identity, version and configuration, not unrestricted opaque command strings.

#### Scenario: Hook disabled

- **GIVEN** a supported upstream project without the optional hook
- **WHEN** ordinary authoring or native import runs
- **THEN** it continues to work and no sealed assurance is required.

#### Scenario: Required producer unavailable

- **GIVEN** a CI policy requiring a producer that cannot run
- **WHEN** the adapter renders results
- **THEN** the missing producer is explicit and the aggregate cannot pass.

#### Scenario: Candidate identity differs

- **GIVEN** producer results for a different commit/tree or configuration
- **WHEN** the action evaluates the current candidate
- **THEN** reuse is rejected and the old result remains diagnostic only.

### Requirement: Loss-aware summaries and SARIF projection

GitHub summaries SHALL show independent producer statuses, exact candidate identity, missing mappings, unavailable checks and native-report links. SARIF 2.1.0 projection SHALL include only suitable located findings and SHALL preserve stable rule identity, original rule/severity, producer identity and original report references. Unlocated obligations and unsupported evidence SHALL remain visible in summaries and authoritative native JSON. Projection SHALL NOT turn advisory convergence into acceptance, fabricate locations or overwrite failed test/security outcomes.

#### Scenario: Advisory convergence masks no failure

- **GIVEN** an advisory converged verdict alongside failed tests
- **WHEN** summary and SARIF are produced
- **THEN** the tests remain failed and overall required verification cannot pass.

#### Scenario: Finding has no source location

- **GIVEN** missing requirement coverage with no valid file/line
- **WHEN** SARIF projection runs
- **THEN** it is retained in native JSON and summary without an invented location.

#### Scenario: Located rule survives projection

- **GIVEN** a located original finding and stable rule ID
- **WHEN** it is projected
- **THEN** rule and location identity and original producer reference survive the round trip.

### Requirement: Least-privilege portable integration

Integration defaults SHALL support local/offline native output without external writes or paid model calls. GitHub publication SHALL require only the scoped permissions needed for selected summary/artifact/code-scanning operations, with third-party actions pinned to immutable revisions. Pull-request execution SHALL NOT execute untrusted candidate code with write credentials through pull_request_target. Unsupported reviewer report formats SHALL be explicit; no universal CodeRabbit/Copilot SARIF contract SHALL be assumed. Native JSON SHALL remain available when code-scanning upload is unavailable.

#### Scenario: Code scanning is unavailable

- **GIVEN** a repository without code-scanning access
- **WHEN** the optional upload step is unavailable
- **THEN** native reports and summaries remain available while the upload limitation is explicit.

#### Scenario: Offline verification

- **GIVEN** released supported commands and local fixtures without network access
- **WHEN** local verification runs
- **THEN** checks execute within their actual supported platform limits without contacting a reviewer or hosted service.
