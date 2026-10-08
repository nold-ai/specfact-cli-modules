# Changelog

All notable changes to this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows SemVer for bundle versions.

## [Unreleased]

### Fixed

- Correct pinned CrossHair 0.0.109 constructor parameter ordering and implicit
  receiver handling while preserving real arguments, upstream merge behavior
  and CLI lifetime. Retain both snapshots' incomplete tool errors and reject
  failure exits without analysis output. Existing deadlines and isolation
  remain required; signed reviewer promotion is still pending.

- Prepare Code Review 0.51.1 portable reviewer bootstrap: corresponding explicit
  tests resolve source-basename ambiguity before fallback selection. The pinned
  Pylint wrapper caches immutable similarity windows only within one bounded
  invocation and restores upstream state on all exits. Required checks, jobs,
  findings and deadlines remain unchanged; publication requires human promotion.

### Added

- Declare the capsule controller cryptography dependency, accept matching
  Python-minor pure wheels, exclude generated environments from complete native
  pytest snapshots, and retain actionable failures when only tests are selected.
  Signature, wheel admission, coverage and selected-path checks remain required.

- Align native complete-pytest coverage roots and selected tests with the admitted
  physical snapshot so test helpers do not become production coverage targets;
  retain missing/low production coverage failures and path-escape rejection.

- Bound OCI gzip read allocations to 1 MiB while preserving signed extraction
  ceilings and all digest/archive checks; large accepted budgets no longer
  trigger an immediate budget-sized allocation on Linux guests.

- Prepare `specfact-code-review` 0.51.0 with a native Darwin/ARM64 managed
  process backend, authenticated candidate capsule cache, offline project
  preparation, and platform-bound analyzer evidence. Local signed test
  candidates execute all ten analyzers on CPython 3.11–3.13. Local native
  pytest results are labeled `project-origin-v1`; protected range
  reviews reject that provenance pending a consumer compatibility change.
  The module's native publication catalogs remain empty until boundary,
  external-project, customer-installation and GHCR acceptance gates pass; this change
  does not yet advertise macOS support. Module signing is performed by the
  protected CI/CD PR follow-up.
- Replace the native per-project acquisition catalog prerequisite with
  project-driven pinned pip wheel resolution, confined PEP 517 root builds,
  offline installation and source-bound coverage imports. Return structured
  discovery diagnostics and preserve verified local cache reuse. Controlled
  native projects use authentic pinned Hatch, uv and Poetry as well; upstream
  Poetry preparation preserves locked Git sources. The complete upstream corpus,
  signed distribution and release acceptance remain pending. Matching
  OS/architecture VMs are valid acceptance environments.
- Correct native Hatch's offline uv target, partial-clone SCM snapshots,
  registry token streaming, relative cache leases, bounded acquisition archive
  parsing, intentionally omitted analyzer payload files and full wheel ABI
  admission. Preserve explicit incomplete evidence for unsupported project
  behavior and all existing protected-review restrictions.
- Preserve native project pytest plugin discovery and version metadata in
  broker-owned parallel children. Adapt the reviewed rerun plugin's failure-count
  IPC to private storage while keeping network denial and strict result
  reconciliation. Expose only the verified packaged uv image for discovery;
  separate managed launch validation and bounded stream handling by responsibility.
- Document the previously published C14 merge-quality range review with immutable scope manifests,
  differential finding continuity, fail-closed analyzer evidence, signed runtime
  contracts, and schema 1.6 report truth. Historical release
  `specfact-code-review` 0.49.59 used strict SpecFact CLI compatibility
  `===0.55.1`; 0.49.61 supersedes that runtime admission rule.

### Fixed

- Release `specfact-code-review` 0.49.76 with fail-closed validation of
  `SPECFACT_CODE_REVIEW_CHANGED_DIFF`, so an unrecognized value cannot select
  an uncorroborated `HEAD` diff and mode drift cannot consume a frozen cached
  identity or weaken changed-line enforcement; retain compatibility
  `>=0.55.1,<1.0.0`.
- Release `specfact-code-review` 0.49.75 with file-level changed anchors for
  empty added staged, cached-tree, and explicitly reviewed untracked files, so
  a line-1 blocker cannot be projected as legacy merely because Git emits no
  text hunk; retain compatibility `>=0.55.1,<1.0.0`.
- Release `specfact-code-review` 0.49.74 with complete analyzer-visible
  worktree identity checks around ordinary changed analysis and every-hop
  cached-tree symlink containment, preventing ignored configuration/import
  support, arbitrary ignored runtime fixtures, symlinked parents, partially
  bound directory-link descendants, or escaping indexed links from changing
  analyzer evidence outside the bound snapshot while retaining stable gitlink
  support;
  retain compatibility `>=0.55.1,<1.0.0`.
- Release `specfact-code-review` 0.49.66 with pre/post raw selected-path and
  immutable `HEAD` tree binding for ordinary worktree analysis, so concurrent
  edits or base advancement cannot project stale blocking findings to PASS;
  retain compatibility `>=0.55.1,<1.0.0`.
- Release `specfact-code-review` 0.49.65 with raw HEAD/worktree corroboration
  that prevents clean filters and index hints from hiding analyzer-visible
  changes, cached enforcement before the first commit through a verified empty
  base tree, and caller-relative cached capsule findings for nested invocations;
  retain the 0.49.64 verdict-preserving ordinary
  changed enforcement when Git line evidence is unavailable, while cached
  immutable-tree enforcement remains required `UNKNOWN`; retain fail-closed
  changed-line evidence discovery plus state-aware, raw, color-free,
  literal-path Git parsing, so
  failed or configuration-altered inspection and hunk content cannot be
  mistaken for a clean diff; normalize repository-root diff paths for nested
  invocations, materialize cached enforcement from one immutable stage-zero
  index tree plus its stable base tree and derive changed lines only from those
  immutable identities so Git filters, index flags, replacement refs, runtime
  worktree mutation, and development-host analyzer mutation cannot change or
  silently detach analyzer input, validate
  local assurance provenance at the runtime boundary, and count explicitly
  reviewed ignored/untracked files as changed.
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
