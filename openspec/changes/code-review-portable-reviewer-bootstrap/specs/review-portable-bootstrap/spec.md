## ADDED Requirements

### Requirement: Explicit correspondence resolves source basename ambiguity

Portable review SHALL honor corresponding explicit test paths before deciding
that a source basename is ambiguous, independently of input order.

#### Scenario: Explicit corresponding tests are present

- **GIVEN** multiple discovered tests share a source basename
- **WHEN** changed input explicitly supplies one or more corresponding test files
- **THEN** selection includes those exact explicit matches in deterministic order
- **AND** an unrelated explicit test does not waive unresolved ambiguity

#### Scenario: No corresponding explicit test is supplied

- **WHEN** multiple discovered tests share the source basename without explicit correspondence
- **THEN** the existing ambiguity error remains blocking

### Requirement: Similarity hash caching preserves upstream review results

The pinned Pylint wrapper SHALL bound similarity hash caching to 256 immutable
LineSet/minimum-line keys within one invocation and retain upstream results.

#### Scenario: Repeated immutable pair comparisons

- **WHEN** the pinned checker compares the same immutable LineSets repeatedly
- **THEN** duplicate groups, locations, statistics, disabled lines and minima match the uncached execution
- **AND** every checker, pair order, jobs configuration, deadline and return code remains unchanged

#### Scenario: Normal or exceptional teardown

- **WHEN** an invocation completes, raises or exits after cache eviction
- **THEN** the upstream function is restored and all cached objects are released
- **AND** no invocation can reuse another invocation's cache


### Requirement: Reviewer installation and host proofs retain ordinary context

The blocking independent reviewer SHALL install the currently available signed
0.51.0 release through the unchanged ordinary marketplace route. Required
ordinary-host recipe assertions SHALL execute explicitly in full and SMART tests;
confined targeted discovery SHALL not select those proof-only host fixtures.

#### Scenario: Retired reviewer pin prevents review execution

- **WHEN** the former 0.50.1 pin is absent from the live registry
- **THEN** select the available authenticated 0.51.0 without overriding signatures
- **AND** retain every existing hosted-recipe, isolation, deadline and error assertion

#### Scenario: Host recipe failure remains blocking

- **WHEN** an explicit ordinary-host proof fails
- **THEN** full and SMART entrypoints preserve its failing exit before portable pytest
- **AND** immutable baseline test bytes remain available while current assertions run in the required host proof; no failure becomes PASS

#### Scenario: Failed hosted preparation retains bounded public evidence

- **GIVEN** the mandatory candidate or independently installed reviewer preparation
- **WHEN** preparation exits successfully without both index runtime descriptors or namespace setup fails
- **THEN** the job remains failing and publishes only fixed preparation status, descriptor-presence and kernel-audit denial booleans, with raw paths/logs remaining private
- **AND** authenticated controller provenance, descriptor binding, namespaces, grants and deadlines remain unchanged

#### Scenario: Core CLI decoration is separate from preparation JSON

- **WHEN** pinned core0.55.4 prints its version and timing around CLI output
- **THEN** hosted preparation invokes the trusted app entry point with the same index scope, project configuration and preparation deadline to obtain undecorated JSON
- **AND** bounded report outcomes distinguish invalid JSON, not-applicable scope and missing descriptor fields/files without publishing raw output or accepting incomplete preparation

#### Scenario: Independent review fails after successful preparation

- **WHEN** the authenticated installed reviewer reaches analysis then exits unsuccessfully
- **THEN** preserve its exit and300-second bound, and publish only finite report outcome/verdict fields, evidence/finding booleans and known diagnostic observations and allowlisted analyzer identities including nested base/head evidence
- **AND** raw reports/logs remain private; missing or malformed reports and observed timeout markers never establish acceptance

#### Scenario: Candidate contracts provide incomplete execution

- **WHEN** contracts fail after successful preparation
- **THEN** project only fixed CrossHair controller-error classes and exception-marker observations from tool_error findings, preserving the original failing exit and all analyzer budgets
- **AND** unrelated tools/categories and raw message suffixes remain private; observations do not establish causation or acceptance

### Requirement: Sealed timeout diagnosis retains execution guards

Temporary candidate CrossHair sampling SHALL retain selected inputs, module
dispatch, checker flags, namespaces and existing deadlines.

#### Scenario: CrossHair times out after successful preparation

- **WHEN** the existing CrossHair target reaches its unchanged timeout
- **THEN** sample only that domain every five seconds and cancel on all exits
- **AND** inspect at most64KiB of captured stderr, publishing only fixed frame-presence observations and preserving UNKNOWN/error
- **AND** do not copy raw stack paths, names or messages; remove sampling after diagnosis and verify the actual correction separately

### Requirement: Invalid pytest requests avoid response-only setup

The portable pytest adapter SHALL decode its request before installed coverage
planning and load response-only controller helpers only when child observations
need them. Selected contracts, coverage ownership checks, command options and
all execution deadlines SHALL remain unchanged.

#### Scenario: Malformed JSON cannot prepare a test command

- **WHEN** a correctly tagged request contains malformed JSON
- **THEN** preserve the existing JSON parsing failure as incomplete tool evidence without coverage planning, response-helper imports or child execution

#### Scenario: Runtime setup fails before child observations

- **WHEN** command preparation fails with an existing caught error
- **THEN** preserve its error finding without loading unused response-only helpers

#### Scenario: Valid observation needs controller response helpers

- **WHEN** a valid request executes the confined child and provides observations
- **THEN** preserve command arguments, coverage bridge fields, findings and all existing coverage/completion checks; load trusted response helpers before resolving the observed root

#### Scenario: Production dispatch follows completed diagnosis

- **WHEN** the candidate commit review passes after the runtime setup correction
- **THEN** remove the temporary stack sampler and its failure projection before promotion
- **AND** retain native module argv, exit codes, existing30/120-second process bounds and2/10-second path bounds; timeouts remain error/UNKNOWN without exposing captured stderr

#### Scenario: Oversized reports retain bounded private diagnostics

- **WHEN** installed or candidate review writes a report exceeding the existing2MiB projection threshold
- **THEN** retain independent oversized_report/unavailable assurance/verdict or the candidate_report_unavailable marker while parsing complete private diagnostics up to32MiB with the standard-library JSON decoder
- **AND** reject invalid or duplicate JSON fields, ignore nested spoofed header keys, bound analyzer rows and finding inspection, and emit only finite known analyzer/snapshot-side/failure-class observations
- **AND** report unavailable diagnostics beyond32MiB; never treat oversized diagnostics as accepted report evidence or disclose private fields
- **AND** preserve the installed controller, original failing exit, grants, checker arguments and all established analysis deadlines


#### Scenario: Decoded non-object pytest JSON avoids unused planning
- **GIVEN** a portable pytest request decodes successfully to a list, string, null, boolean or integer
- **WHEN** the request cannot accept the required coverage mapping fields
- **THEN** perform the native mapping assignment before installed coverage planning and preserve its exact escaping TypeError class/message
- **AND** reject this input before unused planning even when that unused setup would itself fail
- **AND** retain identical bridge objects, ownership fields, serialized command bytes, selected tests and subprocess behavior for valid objects

### Requirement: Incomplete analysis retains all error evidence

The reviewer SHALL preserve incomplete tool execution as error/UNKNOWN evidence and retain both snapshots' tool errors even when ordinary head findings exist.

#### Scenario: Incomplete base findings remain visible beside head findings

- **WHEN** either snapshot is incomplete and the head has ordinary findings
- **THEN** retain every base/head tool-error finding with unknown differential state and retain the existing ordinary head finding selection
- **AND** do not resurrect unrelated ordinary base findings or change unknown assurance, failing exit, analysis selection or deadlines

#### Scenario: CrossHair failure exit has no analysis output

- **WHEN** CrossHair exits1 without analysis stdout, including a constructor crash reported only on stderr
- **THEN** report error/UNKNOWN tool evidence with the original diagnostic instead of returning clean findings
- **AND** preserve valid counterexample/side-effect output handling and existing process/path analysis bounds

### Requirement: Pinned constructor analysis preserves real arguments

The pinned CrossHair0.0.109 dispatch SHALL correct constructor receiver merging
and invalid parameter ordering without discarding real arguments, altering
upstream intersection precedence or changing analyzer selection and deadlines.

#### Scenario: Constructors require valid parameter ordering

- **WHEN** constructor analysis merges variadic and keyword parameters or differing self/cls receivers
- **THEN** remove only implicit receivers before intersection and stable-order final parameters by kind while retaining upstream merge behavior, defaults and annotations
- **AND** preserve explicit class signatures, positional-only inputs, inherited constructors and static/bound initialization arguments

#### Scenario: Native CLI completes or fails

- **WHEN** the existing pinned CrossHair CLI returns, raises or exits
- **THEN** preserve native argv, result/error behavior and restore the original constructor resolver on every exit
- **AND** keep the cloned upstream intersection local, preserve signature validation, and reject unsupported dependency versions without claiming clean analysis
- **AND** run the same analyzer-owned imports, namespaces, contracts, flags and2/10-second path and30/120-second process bounds; retain incomplete error/UNKNOWN on checker failure


### Requirement: Unhashable callable metadata preserves contract parsing

Pinned CrossHair0.0.109 dispatch SHALL permit callable metadata with a declared
unhashable type to pass through the registered-contract parser without a dictionary
lookup crash, while retaining all other contract parsers and registered overrides.

#### Scenario: Pytest marker is callable class metadata

- **WHEN** selected project classes contain a callable pytest marker whose type declares __hash__ = None
- **THEN** return no registered override for that impossible dictionary key and allow the remaining existing parsers to examine real methods
- **AND** preserve hashable registered overrides, ordinary missing lookups and errors raised by custom hash functions or the original registry

#### Scenario: Registered lookup compatibility exits

- **WHEN** the native pinned CLI returns, raises or exits
- **THEN** restore both core and condition-parser lookup aliases on every exit, retain dependency-version rejection, and preserve argv, contracts, namespaces and existing analysis budgets


### Requirement: Temporary diagnosis preserves ordinary dispatch

The temporary sealed diagnostic route SHALL remain default-off and preserve every
ordinary runtime and acceptance policy.

#### Scenario: Renewed sealed diagnosis is default-off

- **WHEN** the protected candidate controller explicitly enables temporary stack diagnosis for the observed remaining CrossHair timeout
- **THEN** transport one actual boolean only through the existing read-only Linux contracts request and a fixed CrossHair-only environment marker, without native schema or permission changes
- **AND** reject non-boolean or true-for-another-member requests; restore sealed-parent state, consume the child marker before attachment, arm five-second stdlib sampling only in this opt-in path and cancel on every exit
- **AND** preserve ordinary request bytes, no-sampler dispatch, stderr-discard timeout behavior, exact CLI arguments, analyzer selection and2/10-second path and30/120-second process budgets
- **AND** project only allowlisted frame-presence codes from the private64KiB stderr tail and retain error/UNKNOWN/original failing exit; diagnostics are not acceptance and temporary transport is removed before promotion


#### Scenario: Sampled processes exit with an error before the deadline
- **GIVEN** opted-in CrossHair has emitted standard-library five-second samples
- **WHEN** it completes with an error or with exit1 and empty analysis stdout
- **THEN** remove only sampled traceback blocks before constructing its error finding, including frames whose legal filenames contain double quotes
- **AND** preserve the actual original process error, error/UNKNOWN, ordinary-mode stderr semantics and finite sampled-frame observations

### Requirement: CrossHair adapter updates invalidate prepared runtimes

Prepared portable runtime identity SHALL include the trusted CrossHair adapter.

#### Scenario: A later adapter correction changes offline reuse policy
- **GIVEN** the source, worker identity, Git identity and all other preparation inputs remain fixed
- **WHEN** only target_crosshair.py changes after a runtime has been cached
- **THEN** derive a different cache identity and reject reuse of the stale prepared runtime in offline mode
- **AND** retain warm reuse when every builder-policy input is unchanged


### Requirement: Absent coverage inputs avoid unused metadata setup

Installed coverage planning SHALL avoid distribution/index setup when no reviewed
input is a Python source, while retaining its original postcondition and every
ownership check for nonempty Python source inputs.

#### Scenario: Empty and non-Python coverage inputs preserve an empty bridge
- **GIVEN** normalized snapshot and site roots and empty or non-Python reviewed inputs
- **WHEN** installed coverage is planned
- **THEN** return exactly the original empty CoverageBridge without loading distribution metadata or walking the snapshot
- **AND** do not shortcut merely because mappings are empty; nonempty Python inputs, including outside-snapshot sources, still use the complete ownership path
- **AND** retain changed-source and duplicate-ownership rejection and all analysis guards
