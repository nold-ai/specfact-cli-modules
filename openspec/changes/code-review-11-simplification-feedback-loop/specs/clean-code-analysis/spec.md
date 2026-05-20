## ADDED Requirements

### Requirement: Clean-code signals can contribute to simplification feedback

The clean-code analysis layer SHALL allow high-confidence `dry` and `kiss` findings to contribute to the simplification feedback queue when they include deterministic rewrite or consolidation evidence. This SHALL NOT change the existing clean-code category semantics or blocking policy.

#### Scenario: High-confidence duplicate shape contributes related locations

- **WHEN** AST clean-code analysis detects duplicate intent with stable related locations
- **THEN** the finding MAY include simplification metadata such as `intent_key`, `rewrite_hint`, and `related_locations`
- **AND** the finding SHALL retain its governed category, such as `dry`, when that category is the primary principle

#### Scenario: Clean-code policy remains unchanged

- **WHEN** a clean-code finding contributes to the simplification queue
- **THEN** its existing category and severity semantics SHALL remain unchanged
- **AND** inclusion in `--focus simplify` SHALL NOT by itself make the finding more severe
