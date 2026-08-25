# Change: Implementation-to-Sealed-Contract Conformance Runtime

## Why

After code is written, teams need a separate deterministic comparison between the implementation evidence and the previously approved preflight contract. That comparison must reuse the sealed contract without pretending the pre-implementation gate proved delivery, and it must remain outside the initial preflight MVP.

## What Changes

- **NEW**: A later `specfact preflight conform <change-id>` runtime that loads a valid preflight seal, captures an implementation snapshot, imports exact test/evidence identities, and evaluates the core conformance contract.
- **NEW**: Python extractors and validators for changed-path, interface, acceptance-criterion, test-intent, task, and exclusion mappings.
- **NEW**: Human and JSON conformance rendering plus optional atomic persistence alongside the original preflight artifacts.
- **NEW**: A workflow handoff for agents to run conformance after implementation evidence is available and before delivery/archive decisions.
- **CLARIFY**: Material implementation drift requires explicit contract reapproval or implementation correction; the runtime does not rewrite the sealed contract automatically.

## Capabilities

### New Capabilities

- `preflight-implementation-conformance-runtime`: Executable postimplementation evidence extraction, comparison, rendering, persistence, and workflow handoff.

### Modified Capabilities

(none)

## Impact

- Planning artifacts only in this phase. No production or test code, module package, manifest, signature, version, workflow asset, generated snapshot/result, adapter, or dependency is created.
- Explicitly excluded from the preflight MVP; work begins only after stable preflight publication and the paired core conformance contract.
- No external harness-specific packaging is included; compatible harnesses consume the canonical workflow through existing adapters later.

## Dependencies

- Parent Feature: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163).
- Blocked by modules `preflight-03-dogfood-hardening-and-release` [#432](https://github.com/nold-ai/specfact-cli-modules/issues/432) and paired core `preflight-05-implementation-conformance` [#684](https://github.com/nold-ai/specfact-cli/issues/684).
- Runs independently of the C15 chain; neither change may silently redefine the other's evidence semantics.

## Explicit Non-Goals

- No pre-implementation readiness, approval, or sealing behavior.
- No automatic contract mutation, implementation edits, or test generation.
- No universal semantic correctness, security, or completeness claim.
- No Codex/ECC/hatch3r adapter packaging.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #434
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/434>
- **Cross-Repository Counterpart**: <https://github.com/nold-ai/specfact-cli/issues/684>
- **Last Synced Status**: proposed
- **Sanitized**: true
