# guided-simplification-review Specification

## Purpose
TBD - created by archiving change code-review-12-guided-simplification-enforcement. Update Purpose after archive.
## Requirements
### Requirement: Simplification findings classify cleanup safety

Simplify-focused review findings SHALL classify each simplification candidate into a guidance kind that tells developers and LLM agents how to act safely.

#### Scenario: Finding describes safe mechanical cleanup

- **WHEN** a deterministic simplification rule identifies behavior-preserving cleanup
- **THEN** the finding SHALL include `guidance_kind="safe_mechanical"`
- **AND** it SHALL include `recommended_action`, `rationale`, `clean_code_principle`, and `safety_checks`
- **AND** the recommended action SHALL be specific enough for an LLM to explain or apply without inferring intent from the free-form message

#### Scenario: Finding preserves meaningful structure

- **WHEN** a candidate occurs in a meaningful contract, interface, public compatibility, CLI boundary, or domain predicate context
- **THEN** the finding SHALL use `guidance_kind="preserve"` or `guidance_kind="design_judgment"`
- **AND** `preserve` findings SHALL include a `preserve_reason`
- **AND** the finding SHALL NOT be eligible for automatic cleanup

### Requirement: Guided simplification reports summarize recommendations and outcomes

Review reports containing guided simplification findings SHALL summarize what was recommended, applied, kept, skipped, failed, and still present.

#### Scenario: Report contains guidance summary

- **WHEN** a simplify-focused run emits guided simplification findings
- **THEN** the report SHALL include a `simplification_summary`
- **AND** the summary SHALL count findings by `guidance_kind`
- **AND** it SHALL count findings by `action_status` when status is present
- **AND** it SHALL include the number of blocking simplification findings under simplify enforcement

#### Scenario: Auto-fix records improvement evidence

- **WHEN** `--focus simplify --fix` applies a safe mechanical rewrite
- **THEN** the resulting report SHALL indicate that the finding was applied or cleared
- **AND** it SHALL record before/after references or improvement evidence sufficient for an LLM to summarize what changed

### Requirement: Interactive simplify prompt adapts to user level

The `/specfact.08-simplify` prompt SHALL adapt guidance depth and confirmation behavior to the user's walkthrough level.

#### Scenario: Prompt asks for walkthrough level

- **WHEN** the prompt starts without an explicit level argument
- **THEN** it SHALL ask whether the user wants vibe-coder, junior developer, senior/pro, or headless-agent guidance
- **AND** it SHALL explain the practical difference between those levels before proceeding

#### Scenario: Headless mode stays conservative

- **WHEN** the prompt or skill is used in headless-agent mode
- **THEN** it SHALL default to review-only behavior unless the user explicitly requested safe automatic application
- **AND** it SHALL apply only findings marked safe for automatic cleanup

### Requirement: Skill carries the guided simplify decision policy

The `specfact-code-review` skill SHALL guide LLMs to interpret simplify-focused findings consistently across IDE and CLI contexts.

#### Scenario: Skill explains action policy

- **WHEN** an LLM uses the `specfact-code-review` skill to act on simplify findings
- **THEN** the skill SHALL instruct it to apply `safe_mechanical`, test `needs_tests`, inspect `design_judgment`, and keep `preserve`
- **AND** it SHALL prohibit treating AI-bloat findings as proof of AI authorship

