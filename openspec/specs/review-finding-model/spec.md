# Review Finding Model Specification

## Overview

The `ReviewFinding` model represents structured code-review findings emitted by the `specfact-code-review` bundle. This specification defines the canonical schema, category enumeration, and tool mapping for all review runners.

## Schema Definition

### Core Fields

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

### Category Enumeration

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

### Tool Enumeration

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

## Category-Tool Mapping

### Clean Code Tools

- `radon`: Emits `clean_code` findings for cyclomatic complexity
- `radon-kiss`: Emits `kiss` findings for LOC, nesting, and parameter counts
- `ast`: Emits `naming`, `kiss`, `yagni`, `dry`, `solid` findings from AST analysis

### Style Tools

- `ruff`: Emits `style` findings for formatting and conventions

### Type Safety Tools

- `basedpyright`: Emits `type_safety` findings for type violations

### Architecture Tools

- `pylint`: Emits `architecture` findings for design issues

### Testing Tools

- `pytest`: Emits `testing` findings for test failures and coverage
- `contract_runner`: Emits `contracts` findings for contract violations

### Checklist Tools

- `checklist`: Emits `clean_code` findings for PR checklist items

## Examples

### KISS Violation

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

### Naming Violation

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

### SOLID Violation

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

## Validation Rules

1. All string fields must be non-empty after stripping whitespace
2. The `line` field must be a positive integer (≥ 1)
3. The `category` field must be one of the enumerated values
4. The `severity` field must be one of: "error", "warning", "info"
5. Tool names should match the official tool enumeration where possible

## Backward Compatibility

This specification is backward compatible with existing `ReviewFinding` consumers. New categories (`naming`, `kiss`, `yagni`, `dry`, `solid`) and tools (`ast`, `checklist`) extend rather than replace the existing schema.