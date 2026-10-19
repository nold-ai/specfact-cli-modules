# Change: Separate quality workflow fixture identities

## Why

Maintainers need the quality matrix to test candidate modules against the declared core dependency while preserving paired-core integration checks. The existing shared checkout selects paired core for the exact-baseline assertion and passes the candidate modules checkout to a smoke verifier that requires its reviewed fixture.

## What Changes

- Keep paired core for existing command, format, lint, contract and smoke checks.
- Check out immutable core 0.55.4 separately and scope its dependency override to the existing Full Test Suite step.
- Include `.github/workflows/pr-orchestrator.yml` in the existing explicitly approved local ARM64 Darwin feature-worktree review deferral eligibility paths. Retain every guard and mandatory blocking exact-head Linux review.
- Read the paired core smoke lock, validate its repository and full commit/tree identities, check out that modules fixture as a sibling, and verify its clean identity before all six launchers run.

## Capabilities

### New Capabilities

- `quality-fixture-identities`: quality workflow steps select the authenticated input appropriate to their existing checks.

## Impact

Only the quality workflow, the local deferral eligibility path list, regression tests and this change's artifacts change. Package source, runtime verifier, manifests, signatures, versions, dependency declarations, coverage, host proof, security prerequisites, minimum-core 0.55.1 matrix and workflow triggers retain their existing contracts. Planning PR #517 and core #770 remain independent.

## Acceptance

Execute the workflow validation steps against disposable Git fixtures, including wrong commit, wrong tree, dirty checkout and malformed lock failures. Prove the original baseline assertion with core 0.55.4 and the original smoke identity check with the paired core lock fixture. Hosted quality acceptance remains pending until CI runs the full suite and all launchers.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #518
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/518>
- **Last Synced Status**: open
- Parent Feature: #163. Assignee: djm81. Project: SpecFact CLI. Issue type: Bug.
- Metadata confirmed 2026-10-16, Europe/Berlin. Initially Todo; parent marked In Progress for this authorized maintenance work. No native blockers or blocked-by edges.
- Scope authorized in the maintenance task. No runtime or policy cutover is authorized.

## Approved local review deferral

On 2026-10-18 (Europe/Berlin), the maintainer explicitly approved the #518 local review deferral proposal and required all checks to remain intact. The exact scope is one additional eligible path, `.github/workflows/pr-orchestrator.yml`, in `scripts/pre-commit-quality-checks.sh`. It already schedules the blocking Linux capsule workflow. The local native review remains UNKNOWN; an eligible local run must report DEFERRED, never PASS. Hosted exact-head review and all existing gates must pass before merge. Core #774 remains separately owned; modules #517 and core #770 remain planning-only.


## Diagnostic follow-up within approved maintenance scope

Expose the existing fixed analyzer-side and CrossHair-class observations for normal structured independent failure reports. Exact-head run 39167860375 identifies contracts as incomplete but omits those fields. This diagnostic-only correction is covered by the maintainer's #518 maintenance authorization with all checks intact. It does not claim to repair the unknown contract fault. Only the reusable workflow projector, its behavioral tests and this change's evidence are added to the current correction scope.


## Portable host interpreter follow-up

Preserve the already approved Darwin ARM64 eligibility when the host has no realpath CLI. Replace that accidental utility dependency with one private portable host path resolver while retaining both candidate-location exclusions before interpreter execution. The current caller-selected policy, complete workflow pin, DEFERRED status, all other hooks and mandatory exact-head hosted checks remain unchanged. No new OS floor, package requirement or capsule capability is authorized. Regression proof precedes source implementation; old-host native acceptance is not inferred from a current-host missing-command simulation.


## External checker completion follow-up

The existing requirement is a working external host Python executing the caller-reviewed immutable checker. Current-head review and a full-hook reproduction show that accepting only a zero exit code also accepts `/usr/bin/true`, which does not execute that checker. Correct the existing execution boundary before reporting DEFERRED. Retain the trusted caller, host process/account and stable filesystem assumptions. This does not authenticate a deliberately malicious host executable or grant protected authority. No policy selection, byte pin, workflow, capability or hosted gate change is included.


## Per-snapshot diagnostic association follow-up (2026-10-19)

Within the existing #518 diagnostic maintenance scope, both inline failure projectors gain an optional `snapshot_diagnostic_observations` value. It associates each incomplete contracts snapshot with its own finite leading producer reason. This is an additive public diagnostic contract, not a new runtime capability. Candidate JSONL appends one envelope; the independent summary adds one field. Empty observations are omitted. Existing fields, lines, acceptance, verdicts, exits and report bounds retain their meaning. The actual hosted contracts cause remains unknown.

The confirmed user is the maintainer diagnosing PR #519 with private controller reports. The input is existing bounded report data, never executable candidate code. Completion for this slice requires both actual workflow heredocs to preserve base/head association, reject suffix promotion and private canaries, and preserve legacy output and exit handling. The selected bounded phase records spec, tests and actual RED before workflow implementation. Planning #517 and core #770 remain untouched.
