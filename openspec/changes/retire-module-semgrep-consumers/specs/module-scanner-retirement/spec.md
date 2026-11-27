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
- **AND** the public Codebase import route accepts the explicit Spec-Kit subcommand and its options, the protocol loads with or without transitions, and the command summary and optional report list the preserved artifacts without advertising the retired preset

#### Scenario: Project import reads OpenAPI examples from test source
- **GIVEN** a Python test with a literal HTTP request, asserted status and asserted JSON response
- **WHEN** Project extracts OpenAPI contracts with or without process workers
- **THEN** the operation contains the request example and response example under the asserted status
- **AND** inline assertions and Flask client contexts preserve supported examples, and repeated operations keep each selected request and response together
- **AND** an existing legacy test-pattern configuration produces migration guidance without invoking Semgrep

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
- **GIVEN** the modules pull request has a paired branch in the public core repository or a commit reaches protected modules `dev`
- **WHEN** native CI prepares the candidate test environment
- **THEN** that environment uses the exact matching core commit for the Repro tests
- **AND** the protected modules `dev` push uses protected core `dev`
- **AND** targeted pytest receives the same checkout path for provenance checks, while unpaired runs retain the released core
- **AND** the independent signed reviewer still uses its own release, core version, and trusted analyzer inputs
- **AND** a pull request changing the native review workflow runs the required module-signature verification for that pull request

#### Scenario: Native contract review completes on import sources
- **GIVEN** changed import sources with Typer constructor annotations and multiple Spec-Kit conversion contracts
- **WHEN** independent native review runs the pinned contract analyzers
- **THEN** CrossHair explores each allowed literal value and runs against each changed Python source within an explicit per-file budget
- **AND** the signed reviewer still checks the contracts and classifies the solver output, and an incomplete subprocess or unrecognized result still blocks the review

#### Scenario: Project feature and quality findings come from the parsed source
- **GIVEN** a Python feature with an HTTP route and a mutable default and a second feature without the quality issue
- **WHEN** Project analyzes the repository without an available Semgrep tool
- **THEN** the first feature retains the route outcome, the quality constraint, and its corresponding confidence evidence
- **AND** the second feature receives no quality constraint from the first
- **AND** endpoint and authentication findings require evidence from the owning source scope, with no inferred route methods or string types when unresolved
- **AND** legacy Project feature or quality configuration produces migration guidance without invoking Semgrep
- **AND** nested classes own their findings, even when Project omits the nested class as a feature
- **AND** otherwise equivalent features independently reflect the HTTP route bonus and mutable-default penalty
- **AND** source evidence distinguishes SQLAlchemy bases from unrelated classes, resolves FastAPI security instances at their binding, and preserves established routes across later import rebinding
- **AND** repeated addition needs a definite string initializer and no preceding write that could leave a non-string value
- **AND** repeated-addition evidence accounts for preceding writes in the loop body
- **AND** function definitions and parameters shadow prior bindings in their Python scopes while defaults and decorators retain their enclosing scope
- **AND** eligible additions in conditional loop bodies appear once and are attributed to their innermost loop
- **AND** writes from earlier iterations can invalidate the initial string evidence unless the current iteration establishes it again
- **AND** unpacked loop targets replace existing evidence for every name they bind
- **AND** assignment values and loop iterables use the bindings that exist before the corresponding targets are assigned
