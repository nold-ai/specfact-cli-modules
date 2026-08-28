# Changelog

All notable changes to this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows SemVer for bundle versions.

## [Unreleased]

### Added

- Document the previously published C14 merge-quality range review with immutable scope manifests,
  differential finding continuity, fail-closed analyzer evidence, signed runtime
  contracts, and schema 1.6 report truth. Historical release
  `specfact-code-review` 0.49.59 used strict SpecFact CLI compatibility
  `===0.55.1`; 0.49.61 supersedes that runtime admission rule.

### Fixed

- Release `specfact-code-review` 0.49.63 with fail-closed changed-line evidence
  discovery, so Git or untracked-file inspection failures cannot be mistaken
  for a clean diff.
- Release `specfact-code-review` 0.49.62 with truthful local capsule scope
  evidence and changed-line enforcement that remains fail-closed for incomplete
  required analyzer evidence.
- Release `specfact-code-review` 0.49.61 with dependency-bounded SpecFact CLI
  compatibility `>=0.55.1,<1.0.0`, so compatible core updates within the
  required module graph do not require another metadata release; retain
  immutable core 0.55.1 as the CI floor proof.
- Reject Ruff operational, configuration, and illegal-argument exits before
  accepting parseable finding JSON as completed analysis evidence.
- Enforce the signed basedpyright project-only invocation and fail closed on
  fatal basedpyright exits plus Semgrep fatal or structured execution errors.
- Close the final C14 promotion blockers for projected policy mounts, staged
  transitive policy selection, Python-only suppression scanning, isolated
  invocation capsules, optional Semgrep skipped-path evidence, governed missing
  Requirements dependencies, and schema 1.6 documentation.
- Documentation: authoritative `docs/reference/documentation-url-contract.md` for core vs modules URL ownership; `redirect_from` aliases for legacy `/guides/<basename>/` on pages whose canonical path is outside `/guides/`; sidebar link to the contract page.
- Add expanded clean-code review coverage to `specfact-code-review`, including
  naming, KISS, YAGNI, DRY, SOLID, and PR-checklist findings plus the bundled
  `specfact/clean-code-principles` policy-pack payload.

### Changed

- Refresh the canonical `specfact-code-review` house-rules skill to a compact
  clean-code charter and bump the bundle metadata for the signed 0.45.1 release.
- Document CI module verification: **`pr-orchestrator`** PR checks run
  `verify-modules-signature` with **`--payload-from-filesystem --enforce-version-bump`**
  and omit **`--require-signature` by default**; **`--require-signature`** is enforced
  when the target is **`main`** (including pushes to **`main`**). **`sign-modules.py`**
  in approval workflows continues to use **`--payload-from-filesystem`**. Sign bundled
  manifests before merging release PRs or address post-merge verification failures by
  re-signing and bumping versions as required.

## [0.44.0] - 2026-03-17

### Added

- Add `--scope changed|full` and repeatable repo-relative `--path` filters to
  `specfact code review run` for deterministic changed-only, full-repository,
  and subtree-limited review selection.

### Changed

- Keep changed-only auto-discovery as the default, allow explicit test subtrees
  to opt matching tests back into scope, and extend the review-run docs plus
  cli-contract scenarios to cover the new targeting controls.

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
