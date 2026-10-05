# Change Validation: preflight-03-dogfood-hardening-and-release (modules)

## Status

**PROPOSAL READY; IMPLEMENTATION NOT STARTED.**

## Planning Boundary

- Proposal-stage governance artifacts only.
- No package source, tests, manifest, registry, signature, version, skill file, generated artifact, adapter, workflow, or release is changed.
- No `TDD_EVIDENCE.md` or release evidence exists because hardening and publication have not started.

## Scope and Ownership Review

- Modules owns evidence-backed runtime/workflow hardening, regression coverage, signing, and stable publication.
- Paired core owns the dogfood protocol and readiness decision.
- External adapters, generated instructions, and postimplementation conformance remain separate downstream ownership.

## Dependency Review

- Parent Feature: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163).
- Native direct blockers verified: modules [#431](https://github.com/nold-ai/specfact-cli-modules/issues/431) and paired core [#683](https://github.com/nold-ai/specfact-cli/issues/683).
- Current rescope (2026-09-20): core #682 -> modules #431; core #683 requires both #431 and independently delivered core C14 #680, then this #432 release. #431 does not block #680.
- Downstream: #432 -> core #684/modules #434. Optional adapters #433 require signed #434 plus independently delivered core #253. #432 does not block C15 #417; #434 does not block generic #251/#253.
- GitHub readback verified User Story type, parent #163, project `SpecFact CLI` / `Todo`, assignee `djm81`, and the required labels.
- Modules C14 #416 is shipped/closed historical context as of the 2026-09-20 rescope; earlier In Progress observations are not current readiness authority.

## Historical Validation Record

The dated checks below are historical observations; they do not approve the
current dependency graph or replace implementation-time verification.

- `openspec status --change preflight-03-dogfood-hardening-and-release --json`: PASS on 2026-08-25; all required proposal artifacts reported complete.
- `openspec validate preflight-03-dogfood-hardening-and-release --strict`: PASS on 2026-08-25.
- Markdown lint limited to changed planning Markdown: PASS on 2026-08-25.
- Staged schema-v2 Requirements planning evidence: PASS on 2026-08-25 with inspection-only cases and no test selectors or execution claims.
- Review follow-up on 2026-08-27: strict OpenSpec validation and schema-v2 Requirements planning evidence PASS after publication order, structured history, exact-core identity, signed workflow/CLI binding, persisted-state rollback, downstream adapter ordering, and C14-status preservation were made explicit; the diff remains planning-only.

## Decision

The proposal is ready for review and a planning-only PR. Hardening, signing, publication, and release evidence remain explicitly unstarted.
