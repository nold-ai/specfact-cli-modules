# Change: Prove Requirement Scenarios with Runtime Test Evidence

## Why

The released Requirements evidence command proves source validity and declared
test-link coverage, but it intentionally does not execute tests or claim
behavioral satisfaction. A linked test file is therefore traceability evidence,
not empirical proof that an exact scenario test was selected, executed, and
passed in the current delivery run.

## What Changes

- Extend Requirements evidence with schema-v2 lifecycle maturity: mapped
  proposal readiness, digest-bound acceptance, test-authored selection,
  failing-first red proof, and final verified proof.
- Require rationale, declared product touchpoints, verification cases, and
  observables from proposal time; exact structured test selectors begin only
  when test automation starts.
- Add a deterministic two-phase public contract: emit a bounded test plan
  before execution, then reconcile trusted JUnit results into the final
  Requirements evidence report.
- Extend the released Code Review public interface with an optional,
  finalized Requirements-evidence context. The review report retains the
  validated provenance separately and never uses the Requirements verdict to
  calculate its own verdict.
- Reject missing, ambiguous, stale, or unsafe selectors; never emit shell
  command strings and never execute a test process from module code.
- Preserve offline-first operation, read-only upstream sources, profile-aware
  severity, deterministic report ordering, and backward-compatible report
  evolution.
- Keep proposal-ready success distinct from implementation proof: a passing
  proposal report explicitly says that execution evidence is not yet available.

## Capabilities

### New Capabilities

- `requirements-scenario-runtime-proof`: Produce deterministic scenario test
  plans and reconcile current-run JUnit results into empirical proof states.

## Impact

- Affected packages: `packages/specfact-requirements` and
  `packages/specfact-code-review`, including public CLI contracts, typed report
  models, tests, version, manifest, registry artifacts, checksums, and
  signatures.
- Affected consumers: the paired core change executes module-produced plans
  and returns JUnit evidence; no core component reimplements proof semantics.
- Affected documentation: Requirements evidence guides on modules.specfact.io,
  including a precise statement of declared versus executed proof.
- Dependencies: extends the released `requirements-06-evidence-enforcement`
  command contract and supplies a bounded input to, but does not implement,
  `validation-02-full-chain-engine`.
- Rollback: keep the existing evidence command/report behavior; no source
  artifacts or tests are modified by evidence evaluation.

## Quality Standards

- Use spec-first and strict failing-before TDD for every public behavior.
- Keep public APIs typed and contract-decorated with deterministic schemas.
- Validate fixture safety, test-plan determinism, JUnit provenance, report
  compatibility, module versions, registry integrity, and signatures.
- Run the full modules quality and fresh SpecFact code-review gates before the
  implementation PR.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#368](https://github.com/nold-ai/specfact-cli-modules/issues/368)
- **GitHub Type**: User Story
- **Parent Feature**: [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161)
- **Parent Epic**: [#144](https://github.com/nold-ai/specfact-cli-modules/issues/144)
- **Project**: SpecFact CLI (`Todo`)
- **Extends**: `requirements-06-evidence-enforcement`
- **Blocks**:
  [nold-ai/specfact-cli#662](https://github.com/nold-ai/specfact-cli/issues/662)
  (native GitHub dependency)
- **Paired Core Change**: `requirements-07-runtime-proof-delivery`
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed / Todo (2026-07-30)
