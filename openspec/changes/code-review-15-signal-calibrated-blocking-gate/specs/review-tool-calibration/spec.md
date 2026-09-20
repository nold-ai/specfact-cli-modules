## Scope rescope — 2026-09-20

Remove optional preflight hardening #432 as a prerequisite. Preserve C14 protected adoption, policy/profile and exception authority, measured calibration, meaningful dogfood checks and signatures. Use current-run results; historical RED and development seals are not required.

This owner-requested planning amendment supersedes conflicting development-workflow and dependency wording below. Runtime behavior is unchanged. Replacement policy: [core #740](https://github.com/nold-ai/specfact-cli/issues/740) and [modules #481](https://github.com/nold-ai/specfact-cli-modules/issues/481).

## ADDED Requirements

### Requirement: Contract Applicability Is Explicit and Semantic

`MISSING_ICONTRACT` SHALL run only for explicitly selected production
paths/symbols and SHALL exclude callables where a missing decorator is not a
meaningful defect.

#### Scenario: Inapplicable public callable is excluded

- **GIVEN** a public callable is a test/stub, property/accessor, serializer, single-call delegate, Protocol/ABC declaration, constrained override, or has no non-receiver input
- **WHEN** contract applicability is evaluated
- **THEN** MISSING_ICONTRACT is not emitted.

#### Scenario: Opted-in concrete boundary remains advisory

- **GIVEN** policy explicitly selects a concrete public production boundary with a non-receiver input and nontrivial body
- **AND** it has no require or ensure contract
- **WHEN** contract analysis runs
- **THEN** one warning-severity MISSING_ICONTRACT finding is emitted
- **AND** it is not promoted to error without a later measured policy revision.

### Requirement: Optional-Parameter Advice Preserves Interface Contracts

The unused optional parameter rule SHALL emit only when signature freedom is
proven.

#### Scenario: Constrained or unresolved method is preserved

- **GIVEN** a method has override/abstractmethod, matches a resolved explicit base/ABC/Protocol member, or has an unresolved base hierarchy
- **WHEN** unused optional parameters are analyzed
- **THEN** no make-required finding is emitted.

#### Scenario: Unconstrained callable may receive advisory guidance

- **GIVEN** a free function or proven unconstrained concrete method has an optional None default that is neither referenced nor checked
- **WHEN** analysis runs
- **THEN** an info, score-neutral unused-optional-param finding may recommend making it required.
