# Design: Signal-Calibrated Blocking Gate

## Scope rescope — 2026-09-20

Remove optional preflight hardening #432 as a prerequisite. Preserve C14 protected adoption, policy/profile and exception authority, measured calibration, meaningful dogfood checks and signatures. Use current-run results; historical RED and development seals are not required.

This owner-requested planning amendment supersedes conflicting development-workflow and dependency wording below. Runtime behavior is unchanged. Replacement policy: [core #740](https://github.com/nold-ai/specfact-cli/issues/740) and [modules #481](https://github.com/nold-ai/specfact-cli-modules/issues/481).

## Ordering and Ownership

C15 consumes C14 schema 1.6 and emits schema 1.7. C14 owns scope truth,
immutable snapshots, typed source locations, identity fingerprints,
occurrence continuity, and protected producer/consumer separation. Policy-02
owns mode and per-rule severity selection. Governance-02 owns exception schema,
approval, scope, and expiry. C15 owns only the code-review adapters from those
contracts to report/exit behavior.

## Verdict Derivation

Normalize analyzer output, attach C14 identity/location/lifecycle, apply the
signed policy, then apply an authenticated exception. Derive aggregate truth in
this order: remaining open error -> `FAIL`; otherwise required uncertainty ->
`UNKNOWN`; otherwise no governed impact -> `NOT_APPLICABLE`; otherwise `PASS`.
For non-shadow enforcement, FAIL and UNKNOWN exit one. Shadow always exits zero
without rewriting aggregate truth. `overall_verdict` is a compatibility
projection and score is never an input.

## Legacy command compatibility

The explicit remove/add delta for command modes retires the general pre-C15
legacy-exit promise, not the flags or report fields. Default enforce and shadow
truth remain; scores/counts cannot resurrect a failure for advisory-only input.
Level filtering uses policy-resolved effective severity for presentation and
does not override aggregate authority or conceal required uncertainty. Invalid
argument combinations still fail normally. The canonical command audit found no
other score/count-based exit promises beyond these and simplify enforcement,
whose separate replacement remains in the same delta.

## Schema 1.7

Each finding retains analyzer-native severity and adds effective severity,
policy rule/profile identifiers and digests, suppression status, and
`occurrence_count`. Exact raw duplicate records remain authenticated by ordered
emission digests. C14's line-independent `identity_fingerprint` remains the
stable key; raw line numbers are evidence, not identity.

The producer groups only identical emissions from the same invocation when
identity, canonical span, severity, blocking inputs, and raw normalized payload
match. It does not merge different tools or rules. Differential comparison
expands `occurrence_count` logically so surplus duplicates cannot disappear.

## Suppression Flow

The Python comment-token parser accepts exactly one canonical rule per
directive, a non-empty reason, and an exception identifier. A trailing comment
targets only its physical line; a standalone comment targets the immediately
following statement or definition. Wildcards and file-wide scope are invalid.

The directive never removes evidence. Warning/info findings may be
acknowledged. An error becomes waived only when governance-02 supplies a
trusted-base exception whose policy rule, canonical path/symbol scope, approval,
and expiry match. Candidate-added approvals are pending and remain blocking.

## Calibration Contexts

Context precedence is test, CLI callback, constrained signature, then general.
C14 supplies test classification. CLI callbacks are resolved from Typer and
Click imports/decorators. A constrained signature is a method with `@override`,
`@abstractmethod`, or a resolved matching member on an explicit base/ABC/
Protocol. Ambiguous policy path scopes are invalid rather than first-match.

Initial signed thresholds:

| Family | Warning | Error |
| --- | --- | --- |
| Radon CC production | 13-25 | >=26 |
| Radon CC test | >=13 | never initially |
| KISS LOC | >80 | never initially |
| KISS nesting production | 4-6 | >=7 |
| KISS parameter count general | 6-9 | >=10 |
| KISS test metrics | threshold exceeded | never initially |
| KISS CLI/constrained parameter count | exempt | never |
| Pylint C0415/C0301 | info | never |
| Pylint E1101 | - | error |
| Other Pylint E/F | advisory | not initially |
| Semgrep swallowed exception | - | error |
| Semgrep eval/exec, os.system, unsafe yaml.load | - | error |
| Context-dependent pickle/password | warning | not initially |

Pylint C0301 is grouped with Ruff E501 as corroborating evidence rather than a
second user-facing finding.

## D1 and D2 Analysis

`MISSING_ICONTRACT` runs only for production paths/symbols explicitly selected
by the policy pack. Eligible callables are public, concrete, have a non-receiver
input, and are not tests, stubs, accessors/properties, serializers, single-call
delegates, protocol/ABC declarations, or constrained overrides. It stays a
warning.

The optional-parameter rule indexes explicit project class hierarchies. It does
not emit when a method is decorated `override`/`abstractmethod`, matches a
resolved base/ABC/Protocol member, or has an unresolved base hierarchy. Only a
proven-unconstrained callable may recommend making the parameter required.

## Simplify enforcement compatibility

C15 explicitly replaces the canonical simplify-enforce rule that blocked every
unresolved safe-mechanical recommendation. Info/warning recommendations remain
visible and fixable but do not block. The blocking count includes only applicable
open unwaived effective errors; required uncertainty remains separately UNKNOWN
and non-passing. Guidance categories do
not promote severity or waive real errors. Guided queue output and deterministic
safe-only rewrites remain unchanged. The explicit removed-old/added-replacement review-run requirements carry
this transition through native archival; runtime/tests migrate during C15
implementation, not this planning PR.

## Rollout

Ship the signed module first in shadow-compatible mode, then ship the pinned
core consumer. Dogfood both repositories in shadow, remediate or approve every
error, and activate blocking only after a reviewed public calibration method and
its acceptance criteria pass. Rollback changes only the policy mode to shadow.

No reproducible frozen audit method or corpus has been recovered. The earlier
40-PR replay, n=150 stratified sample, seed 20260819, at least 40 adjudicated
errors, weighted precision >=80% and Wilson 95% lower bound >=70% are proposed
design targets, not an executable activation rule. Task 5.2 must resolve the
sampling unit, weights/estimand and compatible confidence construction before
sampling; a Wilson calculation on weighted stratified observations is not
specified or implicitly approved here. Public corpus references and a compact
calculation procedure suffice; raw CI transcripts or a new evidence service do
not. Keep shadow until the method is reviewed and its finalized criteria pass.
This one calibration exercise governs C15 blocking activation and relevant
rule/policy changes, not ordinary PR delivery or the independent R09 migration.
