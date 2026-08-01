## Context

`specfact requirements evidence` currently selects changed OpenSpec sources,
imports their requirements, validates profiles, and checks declared test links.
That is a trustworthy static gate, but a path-level link cannot establish that
an exact test was collected or passed. The core repository owns local and CI
process orchestration; modules own Requirements semantics and Code Review
semantics. The boundary must prevent both core-side verdict reimplementation
and module-side execution of repository-controlled command text.

This slice is narrower than `validation-02-full-chain-engine`: it produces one
Requirements scenario-proof signal that the future full-chain graph may
consume. It does not aggregate architecture, contracts, code quality, or other
evidence domains.

## Goals and Non-Goals

### Goals

- Represent every selected scenario with a stable identity and explicit
  touchpoint/test mappings.
- Emit a safe, structured test plan that a consumer can execute without shell
  evaluation.
- Reconcile exact current-run JUnit test cases into deterministic scenario
  proof states.
- Supply finalized Requirements evidence to Code Review as validated context.

### Non-Goals

- Execute pytest, choose CI runners, or own branch-protection policy.
- Infer requirements, touchpoints, or test mappings from code with an LLM.
- Claim that a passing linked test proves every real-world property of a
  requirement.
- Implement the full-chain evidence graph or governance-wide envelope.

## Decisions

### Make lifecycle maturity explicit

Schema-v2 mappings capture rationale, stakeholder references, touchpoints, and
planned verification cases before a test exists. The evaluator reports gate
decision, required maturity, observed maturity, delivery status, and
implementation-evidence status separately. `planned` is a successful proposal
readiness state, never a claim that implementation ran. `accepted` requires a
provider-neutral review record bound to the canonical mapping digest;
`test-authored` requires exact selectors for test cases; `red` and `verified`
are created only by separate JUnit reconciliation.

The mapping digest covers semantic mapping fields, so editing a requirement
mapping invalidates prior acceptance and proof. The module validates and
reconciles evidence only; the core delivery runner supplies trusted review,
Git ancestry, execution, and environment provenance.

### Emit structured selectors, never commands

The plan contains typed selector records rather than executable strings. The
initial runner kind is `pytest`; each selector is an exact repository-relative
test node ID. Selectors beginning with option syntax, escaping the repository,
containing control characters, or relying on shell expansion are invalid. The
plan has a deterministic identifier derived from canonical selected sources,
scenario mappings, and selector records.

### Separate planning from reconciliation

Planning validates sources, scenario identity, touchpoints, and selectors, then
emits a report that can say only `declared` or `selected`. A separate
reconciliation invocation accepts the original plan plus trusted JUnit XML and
records `executed` and `passed`. Missing, duplicate, uncollected, skipped,
failed, or errored exact test cases remain explicit findings governed by the
resolved profile.

The module does not start tests. This keeps process execution, timeouts,
parallelism, and runner hardening in the core delivery layer while retaining
one proof authority.

### Bind results to the current plan

The final report carries the plan identifier, source revisions, result-artifact
digest, and bounded run metadata. For pytest, every JUnit test case must carry a
dedicated canonical selector property containing the collected pytest node ID;
the reconciler does not guess identity from `classname` and `name`. Results
without that property, or identities not present in the supplied plan, are
untrusted. File-level coverage or a similarly named test is not proof.

### Treat touchpoints as declared evidence

Touchpoints identify product interfaces such as CLI commands/options, API
operations, schemas, emitted artifacts, events, or state transitions. They are
explicit inputs with stable identifiers; this change does not infer them from
arbitrary code. Their purpose is to let downstream review compare a changed
surface with its requirement and proof packet.

### Keep review context read-only and subordinate

`specfact code review run` may accept a finalized Requirements evidence file.
It validates schema/provenance and emits deterministic findings when changed
review targets touch declared interfaces with absent or red proof. It does not
change the Requirements verdict, manufacture test results, or silently accept
an invalid packet. Requirements and review reports remain separately auditable.

### Evolve reports compatibly

Existing consumers that need only the current top-level verdict and findings
remain supported. New proof fields are versioned and deterministic. Any schema
version transition includes fixtures proving old-report reading and explicit
rejection of unsupported future versions.

## Risks and Mitigations

- **False proof from path-level matching**: require exact test case identities
  from JUnit, bound to the original plan.
- **Command injection through selectors**: publish structured selectors only;
  validate repository containment and reject option/control syntax.
- **Stale or replayed results**: bind source revisions, plan ID, and result
  digest in the finalized report.
- **Review circularity**: keep Requirements verdict authoritative and review
  context read-only.
- **Over-coupling to the future full-chain engine**: expose a bounded evidence
  packet without importing full-chain orchestration.

## Rollout and Rollback

1. Release planning/reconciliation contracts behind explicit options while
   preserving current evidence behavior.
2. Release optional Requirements context consumption in Code Review.
3. Publish signed module artifacts and an immutable commit for core #662.
4. Let core adopt the release first in advisory mode, then strict policy.
5. Roll back core consumption or optional context input without changing
   upstream requirement sources or deleting retained evidence.
