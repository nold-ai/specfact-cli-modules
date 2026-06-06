# Review Finding Model Specification

## Purpose

The `ReviewFinding` model represents structured code-review findings emitted by the `specfact-code-review` bundle. This specification defines the canonical schema, category enumeration, and tool mapping for all review runners.

## Requirements
### Requirement: ReviewFinding schema defines governed code-review findings

The ReviewFinding model SHALL define core fields, governed categories, tool origins, validation rules, and backward compatibility for structured code-review findings.

#### Scenario: Valid finding payload preserves governed fields

- **WHEN** a review runner emits a finding payload
- **THEN** the payload includes the required governed fields
- **AND** category, severity, tool, rule, file, line, and message values satisfy the validation rules.

#### Schema Definition

#### Core Fields

| Field | Type | Description | Required | Constraints |
|-------|------|-------------|----------|-------------|
| `category` | string (enum) | Governed code-review category | Yes | Must be one of the defined categories |
| `severity` | string (enum) | Finding severity level | Yes | Must be "error", "warning", or "info" |
| `tool` | string | Originating tool name | Yes | Non-empty string |
| `rule` | string | Originating rule identifier | Yes | Non-empty string |
| `file` | string | Repository-relative file path | Yes | Non-empty string |
| `line` | integer | 1-based source line number | Yes | Must be ≥ 1 |
| `message` | string | User-facing finding message | Yes | Non-empty string |
| `fixable` | boolean | Whether finding can be auto-fixed | No | Default: false |
| `confidence` | number | Optional simplification confidence score | No | 0.0 through 1.0 when present |
| `rewrite_hint` | string | Optional suggested simpler idiom or standard pattern | No | Non-empty string when present |
| `canonical_pattern` | string | Optional stable detector pattern name | No | Non-empty string when present |
| `intent_key` | string | Optional deterministic duplicate-intent grouping key | No | Non-empty string when present |
| `estimated_deletion_lines` | integer | Optional estimated net line reduction | No | Must be ≥ 0 when present |
| `related_locations` | array | Optional related source locations for grouped findings | No | Each entry names file and line |
| `signal_trace` | array | Optional detector evidence trace | No | Entries name source/tool and fired status |
| `preserve_reasons` | array | Optional closed-taxonomy reasons to keep structure | No | Values from preserve-reason taxonomy |
| `remediation_packet` | object | Optional AI IDE remediation contract | No | Must satisfy remediation packet requirements |

##### Category Enumeration

The following categories are supported:

- `clean_code`: General clean-code violations (e.g., complexity, readability)
- `security`: Security-related issues
- `type_safety`: Type checking violations
- `contracts`: Contract/precondition violations
- `testing`: Test-related findings (coverage, missing tests)
- `style`: Code style violations
- `architecture`: Architectural concerns
- `tool_error`: Tool execution/parsing errors
- `naming`: Naming convention violations
- `kiss`: KISS principle violations (Keep It Simple, Stupid)
- `yagni`: YAGNI principle violations (You Aren't Gonna Need It)
- `dry`: DRY principle violations (Don't Repeat Yourself)
- `solid`: SOLID principle violations
- `ai_bloat`: Advisory AI-bloat and simplification-defense findings

##### Tool Enumeration

The following tools are officially supported:

- `ruff`: Style and formatting linter
- `radon`: Complexity analyzer
- `radon-kiss`: KISS metrics analyzer
- `semgrep`: Pattern-based static analysis
- `basedpyright`: Type checker
- `pylint`: Architecture and quality linter
- `contract_runner`: Contract validation
- `pytest`: Test execution and coverage
- `checklist`: PR checklist validator
- `ast`: AST-based clean-code analyzer

#### Category-Tool Mapping

#### Clean Code Tools

- `radon`: Emits `clean_code` findings for cyclomatic complexity
- `radon-kiss`: Emits `kiss` findings for LOC, nesting, and parameter counts
- `ast`: Emits `naming`, `kiss`, `yagni`, `dry`, `solid` findings from AST analysis

#### Style Tools

- `ruff`: Emits `style` findings for formatting and conventions

#### Type Safety Tools

- `basedpyright`: Emits `type_safety` findings for type violations

#### Architecture Tools

- `pylint`: Emits `architecture` findings for design issues

#### Testing Tools

- `pytest`: Emits `testing` findings for test failures and coverage
- `contract_runner`: Emits `contracts` findings for contract violations

#### Checklist Tools

- `checklist`: Emits `clean_code` findings for PR checklist items

#### Simplification Metadata

Optional simplification metadata SHALL remain additive to the core finding
schema. Producers MAY include these fields on advisory simplification and
AI-bloat findings, and consumers SHALL ignore unknown optional metadata without
rejecting otherwise valid findings.

The closed preserve-reason taxonomy SHALL contain:

- `compatibility_boundary`
- `public_contract`
- `domain_predicate`
- `test_oracle`
- `performance_sensitive`
- `human_readability`
- `insufficient_confidence`

When `preserve_reasons` is present and non-empty, the finding SHALL NOT be
eligible for automatic cleanup. When `related_locations` is present, each entry
SHALL include a repository-relative `file` and positive integer `line`.

#### Examples

#### KISS Violation

```json
{
  "category": "kiss",
  "severity": "warning",
  "tool": "radon-kiss",
  "rule": "kiss.loc.warning",
  "file": "src/module.py",
  "line": 42,
  "message": "Function `process_data` spans 85 lines; keep it under 80.",
  "fixable": false
}
```

#### Naming Violation

```json
{
  "category": "naming",
  "severity": "warning",
  "tool": "ast",
  "rule": "naming.generic-public-name",
  "file": "src/api.py",
  "line": 15,
  "message": "Public API names should be specific; avoid generic names like process, handle, or manager.",
  "fixable": true
}
```

#### AI-Bloat Advisory

```json
{
  "category": "ai_bloat",
  "severity": "info",
  "tool": "ast",
  "rule": "ai-bloat.manual-loop-comprehension",
  "file": "src/module.py",
  "line": 64,
  "message": "Manual accumulator loop can be expressed as a comprehension.",
  "fixable": false,
  "confidence": 0.91,
  "rewrite_hint": "Consider a list comprehension when the loop has no side effects.",
  "canonical_pattern": "manual_loop_comprehension",
  "estimated_deletion_lines": 3,
  "preserve_reasons": []
}
```

#### SOLID Violation

```json
{
  "category": "solid",
  "severity": "error",
  "tool": "ast",
  "rule": "solid.single-responsibility",
  "file": "src/service.py",
  "line": 28,
  "message": "Function mixes persistence and transport concerns; split repository and HTTP client calls.",
  "fixable": false
}
```

#### Validation Rules

1. All string fields must be non-empty after stripping whitespace
2. The `line` field must be a positive integer (≥ 1)
3. The `category` field must be one of the enumerated values
4. The `severity` field must be one of: "error", "warning", "info"
5. Tool names should match the official tool enumeration where possible
6. Optional simplification metadata must satisfy the type and range constraints in the core fields table
7. `preserve_reasons` values must come from the closed preserve-reason taxonomy

#### Backward Compatibility

This specification is backward compatible with existing `ReviewFinding` consumers. New categories (`naming`, `kiss`, `yagni`, `dry`, `solid`, `ai_bloat`), optional simplification metadata, and tools (`ast`, `checklist`) extend rather than replace the existing schema.

### Requirement: ReviewFinding schema supports additive simplification metadata

The `ReviewFinding` model SHALL accept optional simplification metadata while preserving the existing governed finding fields and category/severity validation. The report schema version SHALL advance additively when simplification metadata, guided simplification metadata, cleanup forecast metadata, or AI IDE handoff metadata is emitted.

#### Scenario: Finding carries signal trace evidence

- **WHEN** a `ReviewFinding` payload includes `signal_trace`
- **THEN** model validation SHALL accept deterministic signal entries with tool/source name, fired status, optional score/value, evidence references, and explanation
- **AND** legacy finding payloads without `signal_trace` SHALL remain valid

#### Scenario: Finding carries preserve reasons

- **WHEN** a `ReviewFinding` payload includes `preserve_reasons`
- **THEN** each reason SHALL come from a closed taxonomy of preserve contexts
- **AND** the finding SHALL NOT be considered safe for automatic cleanup while a preserve reason is present
- **AND** the preserve reason SHALL include enough evidence for a developer or AI agent to explain why cleanup was not applied

#### Scenario: Finding carries remediation packet

- **WHEN** a simplify-focused finding includes `remediation_packet`
- **THEN** the packet SHALL include a plain-language issue, recommended action, possible keep reason, safety checks, validation plan, and safe-to-autofix flag
- **AND** the packet MAY include patch forecast references when preview evidence exists
- **AND** AI IDE prompts and skills SHALL treat the JSON packet as authoritative over prompt prose
