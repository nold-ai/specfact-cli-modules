# Change Validation: preflight-04-harness-adapters

## Status

**PROPOSAL READY; IMPLEMENTATION NOT STARTED.**

## Planning Boundary

- Proposal-stage governance artifacts only.
- No plugin, skill file, command shim, pack, inventory, manifest, hook, workflow, generated instruction, dependency, publication artifact, or external repository contribution is created.
- No `TDD_EVIDENCE.md` exists because implementation has not started.

## Scope and Ownership Review

- This change owns thin Codex, ECC, and hatch3r installation/invocation adapters.
- The signed modules runtime remains the only validator/readiness implementation.
- Core #251 owns generic installation/export and core #253 owns generated instruction references.

## Dependency Review

- Parent Feature: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163).
- Native blocker verified: core [#253](https://github.com/nold-ai/specfact-cli/issues/253), transitively after #251 and the stable modules preflight release.
- GitHub readback verified User Story type, parent #163, project `SpecFact CLI` / `Todo`, assignee `djm81`, and the required labels.
- External upstream issues/PRs are future separately authorized work and do not exist yet.

## Validation Record

- `openspec status --change preflight-04-harness-adapters --json`: PASS on 2026-08-25; all required proposal artifacts reported complete.
- `openspec validate preflight-04-harness-adapters --strict`: PASS on 2026-08-25.
- Markdown lint limited to changed planning Markdown: PASS on 2026-08-25.
- Staged schema-v2 Requirements planning evidence: PASS on 2026-08-25 with inspection-only cases and no test selectors or execution claims.
- Review follow-up on 2026-08-27: strict OpenSpec validation and schema-v2 Requirements planning evidence PASS after immutable adapter identity, authorized trust-root verification, official-installer result consumption, and signed workflow-digest binding were made explicit; the diff remains planning-only.

## Decision

The proposal is ready for review and a planning-only PR. Adapter implementation and external integration remain explicitly unstarted.
