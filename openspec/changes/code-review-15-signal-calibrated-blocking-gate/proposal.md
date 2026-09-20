# Change: Signal-Calibrated Blocking Gate for Code Review

## Scope rescope — 2026-09-20

Remove optional preflight hardening #432 as a prerequisite. Preserve C14 protected adoption, policy/profile and exception authority, measured calibration, meaningful dogfood checks and signatures. Use current-run results; historical RED and development seals are not required.

This owner-requested planning amendment supersedes conflicting development-workflow and dependency wording below. Runtime behavior is unchanged. Replacement policy: [core #740](https://github.com/nold-ai/specfact-cli/issues/740) and [modules #481](https://github.com/nold-ai/specfact-cli-modules/issues/481).

## Why

`specfact code review` can currently emit error-severity findings while returning
exit zero. Score thresholds, `fixable`, enforcement mode, and the core pre-commit
fallback can each override the severity signal. A measured replay over 40 merged
Python PR heads produced 27,147 error findings and zero blocking exits; blind
adjudication estimated 52.1% of error findings actionable, with most noise in
contract, KISS, and Pylint style rules.

The gate needs one auditable contract: an open, applicable, unwaived effective
error blocks non-shadow enforcement; warnings and information remain advisory;
uncertainty fails closed; score never controls the verdict.

## Dependency and Readiness Status

This change follows `code-review-14-scope-truth-and-differential-enforcement`
(C14) and SHALL reuse its schema 1.6 typed locations, finding identity,
differential lifecycle, and protected-consumer boundary. It SHALL NOT implement
parallel scope or continuity logic. Production implementation is blocked until:

- C14 issue [#416](https://github.com/nold-ai/specfact-cli-modules/issues/416)
  completes its implementation and signed handoff;
- the signed C14 module release and paired protected core adoption are shipped;
- `policy-02-packs-and-modes` provides the signed severity/mode authority; and
- `governance-02-exception-management` provides the authenticated, time-bound
  exception contract.

The paired core change is
`nold-ai/specfact-cli:cli-val-07-code-review-gate-adoption`. The originally
proposed `cli-val-06` identifier is unavailable because that sequence number is
already assigned to the parked Copilot test-generation change.

## What Changes

- **NEW**: Review report schema 1.7 records raw and effective severity, the
  signed policy/profile identity, audited suppression state, and duplicate
  occurrence evidence while preserving C14 identity and lifecycle fields.
- **CHANGED**: Non-shadow `changed` and `full` enforcement block on every open,
  applicable, unwaived effective error, including errors with an available
  autofix. Required analyzer or policy uncertainty is `UNKNOWN` and exits one.
- **CHANGED**: Score remains analytics only. Warning/info findings never cause a
  failing verdict; info remains score-neutral.
- **NEW**: Exact `# specfact: suppress[tool:rule] reason="..."
  exception="EXC-..."` directives are retained as evidence. An error is waived
  only by a matching authenticated, active governance exception.
- **CHANGED**: Contract discovery becomes explicit per-rule path/symbol opt-in
  and filters tests, stubs, trivial bodies, protocol/ABC declarations, and
  constrained overrides.
- **CHANGED**: `ai-bloat.unused-optional-param` becomes base-class, ABC,
  Protocol, and `@override` aware and remains score-neutral info.
- **CHANGED**: Radon, KISS, Pylint, and Semgrep severities use a signed,
  measured rule map with deterministic general/test/CLI/constrained contexts.
- **NEW**: Exact same-invocation duplicates are presentation-coalesced with
  occurrence counts and raw digests; C14 multiset multiplicity is preserved.

## Capabilities

### New Capabilities

- `code-review-policy-profile`: signed effective-severity and context mapping.
- `code-review-suppression-evidence`: inline rationale plus approved exception
  matching without candidate-controlled self-waiver.

### Modified Capabilities

- `review-finding-model`: schema 1.7 severity, policy, suppression, and
  occurrence evidence.
- `review-run-command`: deterministic status/exit projection independent of
  score.
- `review-tool-calibration`: contract, AI-bloat, Radon/KISS, Pylint, and Semgrep
  precision corrections.

## Impact

- **Module code**: `packages/specfact-code-review` findings, runner, scorer,
  analyzer adapters, signed policy resources, tests, and user documentation.
- **Core integration**: paired schema 1.7 pre-commit and protected-CI consumer.
- **Compatibility**: schema 1.7 dual-writes legacy verdict/exit fields for one
  release. Schema 1.6 is accepted only in shadow compatibility mode after
  protected enforcement adopts 1.7.
- **Release**: additive public report fields require a minor bundle version
  bump, regenerated signed payloads, and exact tested core compatibility.
- **Rollback**: select advisory/shadow policy mode; retain schema 1.7 evidence
  and do not downgrade or delete findings.
- **Documentation**: update the code-review run and policy/exception guidance
  on modules.specfact.io after production implementation.

## Non-Goals

- No new analyzer family or AI reviewer.
- No blanket blocking of warning or info findings.
- No candidate-controlled or unauthenticated waiver.
- No changes to C14 Git scope, immutable snapshots, differential matching, or
  protected-envelope ownership.
- No generalization claim beyond the measured Python repositories.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#417](https://github.com/nold-ai/specfact-cli-modules/issues/417)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/417>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: GitHub metadata verified; blocked on prerequisite delivery
- **Parent Feature**: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163)
- **Paired Core Change**: [nold-ai/specfact-cli#679](https://github.com/nold-ai/specfact-cli/issues/679) / `cli-val-07-code-review-gate-adoption`
