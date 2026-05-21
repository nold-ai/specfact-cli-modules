## ADDED Requirements

### Requirement: Review findings carry optional simplification metadata

The code-review report SHALL support optional simplification metadata on each finding so IDE prompts can prioritize and explain advisory cleanup without inferring intent from free-form messages. The metadata SHALL be additive and SHALL NOT remove or rename existing `ReviewFinding` fields.

#### Scenario: Finding includes simplification metadata

- **WHEN** a simplification-capable detector emits a finding
- **THEN** the finding MAY include `confidence`, `rewrite_hint`, `canonical_pattern`, `intent_key`, `estimated_deletion_lines`, and `related_locations`
- **AND** each included metadata field SHALL be serializable in `.specfact/code-review.json`
- **AND** existing required fields such as `category`, `severity`, `tool`, `rule`, `file`, `line`, `message`, and `fixable` SHALL remain present

#### Scenario: Consumer ignores simplification metadata

- **WHEN** an existing consumer reads a report containing simplification metadata
- **THEN** the existing consumer SHALL be able to rely on the original required finding fields
- **AND** the metadata SHALL be optional so consumers that do not understand it can ignore it

### Requirement: Simplification analyzers detect deterministic overengineering patterns

The code-review bundle SHALL emit advisory simplification findings for deterministic Python overengineering patterns where a standard language or library pattern is safer and simpler than custom control flow.

#### Scenario: Analyzer flags a verbose pattern with a standard rewrite hint

- **WHEN** the analyzer finds a manual accumulator loop, verbose boolean return, redundant `None` branch, wrapper chain, pass-through defensive `try/except`, one-use temporary, table-lookup candidate, or stdlib replacement candidate
- **THEN** the report SHALL include an advisory simplification finding
- **AND** the finding SHALL include a `rewrite_hint` describing the standard pattern to consider
- **AND** the finding SHALL NOT be emitted at `error` severity

#### Scenario: Analyzer stays silent on ambiguous code

- **WHEN** the analyzer cannot determine a simpler standard pattern with high confidence
- **THEN** it SHALL NOT emit a simplification finding for that code

### Requirement: Duplicate-intent grouping is deterministic and domain-aware

The code-review bundle SHALL group likely duplicate-intent functions only when deterministic static evidence indicates that the functions serve the same business or domain purpose.

#### Scenario: Same-intent functions are grouped

- **WHEN** two or more reviewed functions have compatible normalized AST shapes, compatible call roots or imported APIs, and matching package/domain vocabulary
- **THEN** the review report SHALL include a simplification finding with a stable `intent_key`
- **AND** the finding SHALL include `related_locations` for the other functions in the group
- **AND** the finding message SHALL describe the group as a consolidation candidate rather than a correctness failure

#### Scenario: Similar names alone do not create a group

- **WHEN** two functions have similar names but incompatible AST shape, call roots, or domain context
- **THEN** the duplicate-intent detector SHALL NOT group them solely because of name similarity

### Requirement: Simplification feedback remains advisory and score-neutral

Simplification findings SHALL remain advisory, score-neutral, and non-blocking in v1.

#### Scenario: Simplification-only report remains non-blocking

- **WHEN** a review report contains only simplification findings
- **THEN** those findings SHALL NOT reduce the governed review score
- **AND** the review SHALL NOT fail because of those findings
- **AND** the findings SHALL remain available in `.specfact/code-review.json` for IDE feedback

### Requirement: IDE simplify prompt consumes grouped evidence

The `/specfact.08-simplify` prompt SHALL consume simplification metadata from `.specfact/code-review.json` and use it to guide one confirmed rewrite at a time.

#### Scenario: Prompt groups by intent before proposing rewrites

- **WHEN** `.specfact/code-review.json` contains findings with `intent_key` values
- **THEN** `/specfact.08-simplify` SHALL group candidates by `intent_key`, then by file or domain and rule
- **AND** it SHALL show related locations before drafting a rewrite for a grouped candidate

#### Scenario: Prompt preserves explicit confirmation

- **WHEN** `/specfact.08-simplify` presents a simplification candidate
- **THEN** it SHALL ask the user to accept, reject, skip, or request explanation before applying any edit
- **AND** it SHALL apply only edits the user accepts
