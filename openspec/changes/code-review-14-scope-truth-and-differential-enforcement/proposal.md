# Change: Make Code Review Scope and Differential Enforcement Truthful

## Why

`specfact code review run --scope changed` currently means worktree changes from `git diff HEAD`, not the committed pull-request delta. On a clean PR checkout it can select no committed files. Git resolution failure becomes an empty changed-line map, allowing blocking findings to be treated as legacy and producing a green exit.

The report also lacks an honest unknown/not-applicable state, conflates autofix availability with resolution, and determines introduction primarily through changed-line intersection. These are evidence-boundary defects that must be fixed before adding more review rules.

## What Changes

- Define explicit scope sources: `worktree`, `index`, `range`, `full`, or positional files. Keep `changed` only as a deprecated alias for `worktree`.
- Require full base/head refs for range scope and derive the PR delta from the merge base.
- Emit immutable scope evidence and fail closed as `UNKNOWN` when Git scope cannot be resolved.
- Include changed tests by default for range review; exclusions are explicit evidence.
- Analyze base and head with the same pinned analyzer/config identities and classify findings as introduced, fixed, unchanged, or unknown using stable fingerprints.
- Report mandatory analyzer coverage and make skipped/failed mandatory tools `UNKNOWN`.
- Separate finding severity, lifecycle status, autofix availability, and blocking policy.
- Use `PASS`, `FAIL`, `UNKNOWN`, and `NOT_APPLICABLE` truthfully; waivers remain a governance overlay.

## Capabilities

### Modified Capabilities

- `review-run-command`: Resolve explicit snapshot scopes and perform deterministic base/head differential review.
- `review-finding-model`: Separate lifecycle, remediation availability, differential disposition, and policy.
- `review-cli-contracts`: Prove range selection, unknown handling, differential classifications, and analyzer coverage.

## Impact

- Planning artifacts only. No package source, tests, manifests, registry, version, signatures, prompts, or generated docs change in this commit.
- Later implementation changes the public review CLI and JSON schema additively, with a deprecation path for `--scope changed`.
- CI integrations must migrate to `--scope range --base-ref <base> --head-ref <head>` or explicit positional files.
- Rollback: retain the legacy alias and dual-write old/new report fields during one compatibility release.

## Explicit Non-Goals

- Add or change individual Ruff, Radon, Semgrep, basedpyright, pylint, contract, or AI-bloat detectors.
- Fuse Requirements verdicts into Code Review.
- Perform LLM review or claim semantic completeness.
- Infer historical pytest dependency closure.
- Implement the global governance evidence graph.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Origin**: dogfooding analysis of core PRs #665–#671
- **Flagship track**: deterministic code review and AI-bloat defense foundation
- **Planning date**: 2026-08-13

