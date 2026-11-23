## ADDED Requirements

### Requirement: Module scanner entry points operate without Semgrep
SpecFact-owned Project and Codebase entry points SHALL run supported feature, quality, import and async operations without Semgrep. Prior supported diagnostic, output and fix behavior SHALL retain fixture-backed compatibility or an explicit documented migration. Unsupported legacy configuration or a required replacement failure SHALL remain visible.

#### Scenario: Project analysis and repro do not invoke the retired engine
- **GIVEN** signed candidate modules in an external installation without Semgrep and representative Project and Codebase fixtures
- **WHEN** the normal analysis and repro commands run
- **THEN** expected findings and safe controls remain distinguishable, supported fix behavior remains explicit, and no retired scanner executes or is provisioned

#### Scenario: Project imports preserve supported artifacts without a scanner
- **GIVEN** a source project with HTTP request and response test examples and a Spec-Kit project eligible for protocol and workflow generation
- **WHEN** the Project import commands run in an external installation without Semgrep
- **THEN** supported request, response and status-code examples appear in the OpenAPI contract, and Spec-Kit import writes its supported protocol and workflow without generating a Semgrep preset or invoking the scanner

#### Scenario: Prior scanner configuration needs migration
- **GIVEN** a reviewed project requests a formerly supported Semgrep configuration or fix the replacement cannot interpret
- **WHEN** the affected check resolves its configuration
- **THEN** the check reports the unsupported setting and a migration remedy without claiming successful coverage or changing source unexpectedly

#### Scenario: Codebase repro runs the installed core async analyzer
- **GIVEN** a project with Python async code and either an explicit async check request or the standard legacy async policy
- **WHEN** the user runs the normal Codebase `repro` command without Semgrep installed
- **THEN** the command uses the installed core analyzer, reports structured async results, and requires a successful scan
- **AND** an unrecognized policy, unavailable core analyzer, or unsupported automatic fix reports an actionable failure without modifying Python source
- **AND** projects with no async request or legacy policy retain their existing check set

#### Scenario: Native tests use the paired core with the analyzer
- **GIVEN** the modules pull request has a paired branch in the public core repository
- **WHEN** native CI prepares the candidate test environment
- **THEN** that environment uses the exact matching core commit for the Repro tests
- **AND** the independent signed reviewer still uses its own release, core version, and trusted analyzer inputs
