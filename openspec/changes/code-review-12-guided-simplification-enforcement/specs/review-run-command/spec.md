## MODIFIED Requirements

### Requirement: Review run supports simplify focus

The `specfact code review run` command SHALL accept `--focus simplify` as a targeted review focus for simplification feedback. The focus SHALL retain findings that belong in the simplification queue and SHALL classify them with actionable guidance.

#### Scenario: Simplify focus emits guided simplification queue

- **WHEN** `specfact code review run --focus simplify --json --out .specfact/code-review.json` completes
- **THEN** the JSON report SHALL retain simplification-focused findings
- **AND** retained findings SHALL include guidance metadata for actionability, preservation, or design judgment
- **AND** the report SHALL include a simplification summary when guided findings are present

#### Scenario: Simplify enforce blocks only safe mechanical debt

- **WHEN** `specfact code review run --focus simplify --mode enforce` runs
- **THEN** the process SHALL fail only when unresolved findings with `guidance_kind="safe_mechanical"` remain
- **AND** findings classified as `needs_tests`, `design_judgment`, or `preserve` SHALL NOT make the run fail

#### Scenario: Simplify fix applies only safe mechanical rewrites

- **WHEN** `specfact code review run --focus simplify --fix` runs
- **THEN** automatic rewrites SHALL be limited to deterministic safe-mechanical findings
- **AND** the command SHALL rerun review after applying rewrites
- **AND** the JSON report SHALL record applied, failed, and still-recommended outcomes
