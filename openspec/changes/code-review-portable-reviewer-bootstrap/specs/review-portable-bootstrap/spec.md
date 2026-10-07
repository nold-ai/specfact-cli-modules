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
