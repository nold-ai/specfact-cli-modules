# Tasks: canonical house-rules skill installation

## 1. Analysis and Setup

- [x] 1.1 Confirm the current updater writes noncanonical IDE mirrors and raw Cursor
  `.mdc` output
- [x] 1.2 Add OpenSpec change coverage for this bugfix scope before editing code

## 2. Implementation

- [x] 2.1 Refactor the updater so bundled `SKILL.md` content resolves into
  `skills/specfact-code-review/SKILL.md` as the canonical project artifact
- [x] 2.2 Add explicit canonical IDE target selection instead of blanket mirroring
- [x] 2.3 Render Cursor `.mdc` output with Cursor rule metadata and the skill body
- [x] 2.4 Update the command flow so `rules update` refreshes only installed targets
  unless an IDE is explicitly selected

## 3. Tests and Docs

- [x] 3.1 Update unit tests for canonical target selection and Cursor rule rendering
- [x] 3.2 Correct the module docs so they no longer promise unsupported IDE paths

## 4. Evidence

- [x] 4.1 Run targeted unit tests for the rules updater/commands
- [x] 4.2 Record failing/passing evidence in `TDD_EVIDENCE.md`
