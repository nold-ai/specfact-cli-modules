## ADDED Requirements

### Requirement: Simplify review reports include cleanup forecasts

Simplify-focused review reports SHALL include a cleanup forecast that quantifies likely cleanup impact without treating estimates as guaranteed deletions.

#### Scenario: Forecast summarizes reviewed LOC and deletion estimates

- **WHEN** `specfact code review run --focus simplify --json` emits guided simplification findings
- **THEN** the report SHALL include `cleanup_forecast.reviewed_loc`
- **AND** it SHALL include low, expected, and high estimated deletion-line totals
- **AND** it SHALL include deletion estimates grouped by `guidance_kind`
- **AND** legacy report consumers SHALL still be able to ignore the new field

#### Scenario: Forecast exposes normalized AI-bloat index

- **WHEN** a cleanup forecast is present
- **THEN** it SHALL include normalized metrics per KLOC for finding density, weighted bloat points, and cleanup yield
- **AND** the default weights SHALL be `safe_mechanical=1.0`, `needs_tests=0.6`, `design_judgment=0.25`, and `preserve=0.0`
- **AND** preserve findings SHALL contribute no weighted bloat points

### Requirement: Cleanup forecasts distinguish advice from proof

The cleanup forecast SHALL distinguish estimate-only signals from previewed or mutation-backed proof.

#### Scenario: Preview evidence upgrades forecast confidence

- **WHEN** `--preview-fixes` computes a patch forecast for safe-mechanical findings
- **THEN** the cleanup forecast SHALL include preview evidence for affected findings
- **AND** the preview SHALL report added, removed, and net line counts without editing tracked files

#### Scenario: Mutation evidence is opt-in

- **WHEN** `--with-mutation` is not provided
- **THEN** the review SHALL NOT run mutation testing
- **AND** the report SHALL NOT imply mutation-backed proof exists

- **WHEN** `--with-mutation` is provided for simplify focus
- **THEN** mutation outcomes SHALL be recorded as evidence for candidate findings
- **AND** timeouts or unavailable mutation tooling SHALL be recorded as inconclusive rather than safe cleanup proof
