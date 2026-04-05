# house-rules-skill Specification

## Purpose
TBD - created by archiving change clean-code-02-expanded-review-module. Update Purpose after archive.
## Requirements
### Requirement: House-rules skill exposes the compact clean-code charter
The canonical `skills/specfact-code-review/SKILL.md` surface SHALL include the 7-principle clean-code charter in a compact format suitable for downstream IDE integrations.

#### Scenario: Skill refresh keeps the charter compact
- **GIVEN** the canonical review skill is rendered or updated
- **WHEN** the clean-code charter is included
- **THEN** the skill keeps the charter within a compact house-rules format
- **AND** existing non-overlapping guidance such as TDD-first and contract discipline remains present

#### Scenario: Downstream IDE aliases can reference the skill without duplicating it
- **GIVEN** another repository such as specfact-cli generates lightweight IDE instruction aliases
- **WHEN** those aliases reference clean-code guidance
- **THEN** the canonical review skill remains the source of truth
- **AND** downstream aliases only need a short reference to the skill

