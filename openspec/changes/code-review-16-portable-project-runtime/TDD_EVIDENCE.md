# TDD evidence

Implementation begins from dev 976460c0541b685f5fae256faef4cec32fe9ba7e on 2026-09-14 (Europe/Berlin). The original customer reproduction is inaccessible; no external execution success is claimed. Record each mapped failing-before run before its production changes and passing-after evidence below.

## Discovery — failing before production changes

`hatch run pytest -q tests/unit/specfact_code_review/run/test_runtime_discovery.py` failed collection with `ModuleNotFoundError: specfact_code_review.run.runtime_discovery` (12 cases planned). No discovery production implementation existed. Output retained in DISCOVERY_RED.txt.

## Discovery passing / artifacts failing

Discovery: 12 passed in 0.10s. Runtime artifact/adapter tests failed collection before production changes: ModuleNotFoundError runtime_artifacts. See ARTIFACTS_RED.txt.

## Artifact passing / builder failing

18 discovery/artifact/adapter tests passed in 0.11s. Builder/source-copy tests fail before implementation with ModuleNotFoundError runtime_builder; see BUILDER_RED.txt. Builder versions verified against PyPI JSON on 2026-09-14: pip 26.2.1, uv 0.12.13, Hatch 1.18.0, Poetry 2.4.3.

## Worker and CLI failing before integration

Worker tests fail collection for missing portable_worker. All three CLI tests fail: missing runtime command, missing handoff options, and rejected project_config/project_runtime kwargs. See WORKER_RED.txt and CLI_RED.txt.

## Snapshot integration failing

Seven CLI/worker tests pass; automatic snapshot attachment fails before production integration with missing portable_snapshot. See SNAPSHOT_RED.txt.

## Immutable pair failing

Independent pair test fails for missing run_project_scope_pair; two other snapshot tests pass. Existing command/runner/sandbox/tool regressions: 511 passed, 14 failed. Failures identify accidental ScopeRequest option forwarding and legacy mocked runtimes entering the newly added preparation boundary. Preserve original legacy assertions and isolate their new dependency boundary.

## Runtime hardening and real external preparation

Additional failing-before artifacts cover pytest configuration precedence and execution/coverage evidence; changed local workspace source; safe internal symlinks; explicit dependency groups; customer Actions source layouts; worker PID/mount isolation; worker identity attachment; native library inventory; credential-free dependency inventory; native Git builder support; analyzer/project dependency conflicts; and dependency-only immutable ranges. Each corresponding `*_RED.txt` was captured before retaining its implementation.

On 2026-09-14, 49 portable-runtime/corpus unit tests passed in 0.31 seconds; the subsequently added worker identity and compatibility scenarios passed separately. Scope plus portable snapshot regressions passed 130 tests in 9.90 seconds. Formatting, typing, lint, manifest/YAML validation, bundle import checks, development checksum/version checks, and strict OpenSpec validation passed before the first full-suite run.

The first complete suite reported 1,972 passed and 22 failed in 75.63 seconds. Five failures were caused by the existing paired core checkout being 0.54.0, below this bundle's already-declared >=0.55.1 requirement. Fifteen Semgrep cases could not load macOS trust anchors. Two failures identified missing command documentation/generated command artifacts. Verification now uses a separate checkout of public core 0.55.4 at d5799705, an explicit certificate bundle, and regenerated documentation; rerun evidence follows.

Real non-root Ubuntu 24.04 x86-64/Python 3.12 preparation succeeded for all four exact pinned upstream repositories: Requests/pip, Hatch/hatch-test, Flask/uv, and Poetry/test. The controller used public core 0.55.4 and the signed 0.49.85 base, with this worktree's development preparation implementation. This is acquisition/bootstrap evidence, not updated signed analyzer or release acceptance. Hatch first exposed missing Git and then its newer glibc requirement; Git now runs with its own private loader/library closure, leaving the supervisor's runtime unchanged.

The dedicated worktree was moved to `/private/tmp/specfact-473-worktree` after automatic approval-service timeouts on edits outside writable roots. Branch identity and all uncommitted changes were preserved; the main dev checkout remains untouched.

## Review-driven corrections and current delivery boundary

The corrected core/certificate/documentation baseline passed 1,994 tests in 95.74 seconds; smart tests passed the same 1,994 tests and contracts passed 28 tests (1,966 deselected). Subsequent review-driven changes require fresh evidence and do not inherit those passing claims.

The active worktree is now `/private/tmp/specfact-473-implementation`, with writable Git metadata in `/private/tmp/specfact-473-git.git`, the same feature branch and base, and canonical pre-commit hooks installed. Its task-owned development virtualenv symlink is locally excluded from Git. The user checkout remains untouched.

Additional failing-before artifacts record native Python CLI handoff and fail-closed startup, in-repository parent requirements includes, verified active environment selection, exact signed-interpreter patch constraints, and complete external analyzer-roster validation. Grouped adapter/CLI/worker tests were split into corresponding module test files; historical failing transcripts retain their original filenames.

A fresh bug-hunt review exposed an invalid development-only BasedPyright command combining `--venvpath` and `--pythonpath`. That report is not passing analyzer evidence. A real BasedPyright subprocess regression now verifies the corrected `--pythonpath` invocation and dependency imports (9 focused command tests passed). The later full run found 16 failures: foreign Hatch activation, four test observers still reading parameters moved into snapshot settings, and five worktree-identity tests rejecting the task's untracked virtualenv symlink. Discovery now verifies the active environment belongs to the reviewed root; observers inspect the equivalent settings fields; local Git exclusion fixes the task environment without relaxing source identity rules. Runner/discovery verification passed 424 tests in 12.63 seconds after these corrections.

Open acceptance work remains: full updated capsule execution across all twelve Linux corpus combinations, the labelled reconstructed Hatch/native fixture, member-specific dependency closure isolation, interpreter selection across differing base/head constraints, complete preparation/cache failure cases, and published signed installation acceptance. Successful preparation of four cp312 environments does not satisfy these criteria. This change must remain open and any initial PR must remain draft until acceptance and review are complete; #472 additionally requires access to and validation of the original customer reproduction.

Latest local full run on 2026-09-14: `hatch run test` with public core 0.55.4 and the explicit CA bundle passed **2,008 tests in 81.90 seconds**, with two pre-existing lark deprecation warnings. Contract tests passed **28 tests**, with 1,980 deselected. Formatting and typing passed. Formal development verification passed with `--payload-from-filesystem --enforce-version-bump --allow-missing-public-key --version-check-base refs/remotes/origin/dev`, matching the canonical branch-aware hook; this is not a release-signature claim.

Smart-test verification subsequently passed **2,008 tests in 82.95 seconds**. The development virtualenv lacked CrossHair, causing the review tool to discover a globally installed executable using a different interpreter. Installed the capsule-pinned `crosshair-tool==0.0.109` into the task-owned virtualenv; fresh review must be rerun with that environment. Earlier advisory reports containing the CrossHair import error are not complete passing analyzer evidence.

The staged-snapshot pytest failure was isolated to `test_github_candidate_context_failure_never_uses_stale_official_payload`: it depended on the caller checkout containing `.git`. The test now constructs its own publisher-checkout fixture and preserves the original fail-closed assertions. Recorded failing transcripts are normalized only for trailing whitespace; their outcomes and diagnostics are unchanged.
