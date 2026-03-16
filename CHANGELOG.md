# Changelog

All notable changes to this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows SemVer for bundle versions.

## [0.43.0] - 2026-03-16

### Added

- Add the fully wired `specfact code review run` command with JSON, score-only,
  fix, and git-diff default file discovery behavior.
- Add clean and dirty review fixtures, end-to-end command tests, and
  cli-contract scenario YAML files for the review `run`, `ledger`, and `rules`
  command groups.

### Changed

- Extend the code-review module docs with review-run usage, output, exit-code,
  and piping examples.
- Add a repo-local CLI contract schema validator and bump the signed
  `specfact-code-review` bundle metadata for the new command integration.

## [0.42.1] - 2026-03-16

### Added

- Add `specfact code review rules show|init|update` to manage a generated
  `skills/specfact-code-review/SKILL.md` house-rules skill from recent ledger
  history.

### Changed

- Document the house-rules workflow, including the 35-line skill budget and the
  optional `.cursor/rules/house_rules.mdc` mirror updated from ledger data.

## [0.42.0] - 2026-03-16

### Added

- Add a `specfact-code-review` reward ledger with Supabase-first persistence,
  local JSON fallback, and `ledger update|status|reset` commands under
  `specfact code review`.

### Changed

- Document the new ledger workflow, including the review-report pipe and the
  offline fallback path used when Supabase is not configured.

## [0.41.5] - 2026-03-13

### Added

- Add `contract_runner` and review orchestration helpers to `specfact-code-review`, including icontract AST checks,
  CrossHair fast-pass handling, and a TDD gate for missing tests or low coverage.

### Changed

- Extend the code-review bundle docs with contract/TDD gate behavior and bump the signed
  `specfact-code-review` bundle metadata for the new runner set.

## [0.41.4] - 2026-03-13

### Added

- Add `basedpyright` and `pylint` review runners to `specfact-code-review` for governed type-safety and architecture findings.

### Changed

- Document the new code-review tool runners and bump the `specfact-code-review` bundle patch version for the signed module update.
