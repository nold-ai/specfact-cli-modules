# Change Validation: preflight-05-implementation-conformance (modules)

## Status

**PROPOSAL READY; IMPLEMENTATION NOT STARTED.**

## Planning Boundary

- Proposal-stage governance artifacts only.
- No production code, tests, module package, manifest, signature, version, workflow asset, generated snapshot/result, adapter, or dependency is created.
- No `TDD_EVIDENCE.md` exists because implementation has not started.

## Scope and Ownership Review

- Modules owns worktree/index checkpoint and immutable-range conformance execution, Git/pytest/review evidence import, caching, remediation packets, bounded agent workflow, pre-commit integration, rendering, persistence, signing, and publication.
- Paired core owns snapshot kinds, obligation mapping, finding/result, authority, and pure verifier interfaces.
- The work follows stable preflight publication and precedes #251/#253/#433. It packages no external harness adapter and does not alter C15 semantics.

## Dependency Review

- Parent Feature: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163).
- Native blockers to verify: stable modules [#432](https://github.com/nold-ai/specfact-cli-modules/issues/432) and paired core [#684](https://github.com/nold-ai/specfact-cli/issues/684).
- Native downstream to add: core [#251](https://github.com/nold-ai/specfact-cli/issues/251), followed by #253 and modules #433.
- Delivery ordering records core #682 -> modules #431 -> core #680/#683 -> modules #432 -> core #684 -> modules #434 -> core #251/#253 -> modules #433; exact released identities must be read back again before implementation.
- GitHub readback verified User Story type, parent #163, project `SpecFact CLI` / `Todo`, assignee `djm81`, and the required labels.

## Validation Record

- `openspec status --change preflight-05-implementation-conformance --json`: PASS on 2026-08-25; all required proposal artifacts reported complete.
- `openspec validate preflight-05-implementation-conformance --strict`: PASS on 2026-08-25.
- Markdown lint limited to changed planning Markdown: PASS on 2026-08-25.
- Staged schema-v2 Requirements planning evidence: PASS on 2026-08-25 with inspection-only cases and no test selectors or execution claims.
- Review follow-up on 2026-08-27: strict OpenSpec validation and schema-v2 Requirements planning evidence PASS after base/head seal semantics, explicit implementation identity, the complete delivery chain, C14-status preservation, and signed-release adapter compatibility were aligned; the diff remains planning-only.
- Review follow-up on 2026-08-30: shadow evidence is bound to the exact promotion candidate and invalidated by relevant changes; implementation-branch release proof uses a projected registry row while official registry mutation remains post-merge publication work.
- Second review follow-up on 2026-08-30: release preparation and release-matrix fixes force rollout-evidence recollection for the final unchanged candidate; interface additions, deletions, and rename endpoints use provenance-bound absent-side tombstones rather than missing evidence.
- Third review follow-up on 2026-08-30: publication preserves or derives the exclusive core-compatibility upper bound from the complete bundled-module dependency intersection, keeps the complete range identical across manifest and registry, and tests rejection at and above that bound as well as lower-bound behavior.
- Fourth review follow-up on 2026-08-30: checkpoint applicability is derived from the selected snapshot so worktree-only unstaged/untracked changes cannot be skipped; staged-only selection remains pre-commit/index-specific. Scope-expansion recovery removes already-implemented production expansion before successor approval and failing-first evidence, then permits reimplementation only afterward without automatic code/history/seal mutation.

## Decision

The proposal is ready for review and a planning-only PR. Checkpoint, pre-commit, bounded workflow, publication, and final conformance runtime work remain explicitly unstarted.
