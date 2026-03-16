# Change: Canonical house-rules skill installation for code-review

## Why

The current `specfact code review rules` flow writes the bundled house-rules skill
into multiple IDE-specific paths regardless of the chosen environment and copies raw
`SKILL.md` content into Cursor's `.mdc` rule file. That breaks the intended source of
truth model, conflicts with upstream IDE installation flows, and fails to produce a
Cursor rule that auto-attaches correctly.

## What Changes

- Keep `skills/specfact-code-review/SKILL.md` as the canonical project skill output
- Resolve bundled package `SKILL.md` content into that canonical path first
- Install to one canonical IDE target only when the user explicitly chooses an IDE
- Render `.cursor/rules/house_rules.mdc` with Cursor rule metadata instead of raw
  `SKILL.md` frontmatter
- Make `rules update` refresh only already-installed canonical IDE targets unless an
  explicit IDE target is supplied

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `code-review-rules`: canonical house-rules installation and Cursor rule rendering

## Impact

- Affected: `packages/specfact-code-review/src/specfact_code_review/rules/`
- Affected tests: `tests/unit/specfact_code_review/rules/test_updater.py`
- Affected docs: `docs/modules/code-review.md`
