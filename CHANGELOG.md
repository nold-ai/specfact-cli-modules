# Changelog

All notable changes to this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows SemVer for bundle versions.

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
