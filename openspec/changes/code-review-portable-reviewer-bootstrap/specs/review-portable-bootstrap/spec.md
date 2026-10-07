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
