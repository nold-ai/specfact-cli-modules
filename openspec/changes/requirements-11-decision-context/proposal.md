# Change: Preserve optional requirement decision context

## Why

Apply the owner-approved agentic SDLC roadmap to existing Python, OpenSpec/Spec Kit and GitHub users. Preserve the distinction between reviewed assertions, behavior evidence and authenticated authority. This is a bounded follow-up, not a replacement authoring or review engine.

## What Changes

- Optional versioned decision context: The system SHALL provide a versioned RequirementDecisionContext companion to existing requirement inputs. Version 1 records SHALL retain stable record IDs, typed assumption/clarification-decision kinds, explicit disposition, original source references and source digests, and typed links to requirements, acceptance cases, components or ADRs. It SHALL reuse existing clarification question/answer/integration records rather than create a competing clarification workflow. Owner, review date and falsifying verification links SHALL remain optional in ordinary use. Records SHALL represent explicit source assertions only; unrecorded assumptions SHALL NOT be invented or claimed discovered.
- Separate decision context identity: Decision-relevant content SHALL have a separately versioned canonical digest over normalized IDs, kinds, dispositions, question/answer or assumption statements, typed links and explicit verification references. Source content digests SHALL bind the imported assertion to its original artifact. Historical session timestamps and other non-decision metadata SHALL NOT change the decision digest unless explicitly selected by policy. Legacy plan hashes SHALL remain unchanged and SHALL continue to exclude clarifications. A changed bound decision or source digest SHALL invalidate reuse of evidence that binds that context; an absent optional context SHALL NOT invalidate ordinary legacy evidence.
- Assertions and assurance authority remain distinct: Imported dispositions and answered_by/owner strings SHALL NOT authenticate approval. Ordinary evaluation SHALL report a touched unresolved recorded assumption as advisory. An explicitly selected assurance policy MAY require resolution, ownership, review date or verification links. Unavailable or ambiguous required evidence SHALL remain UNKNOWN; a reconciled behavioral contradiction SHALL remain FAIL. A trace link SHALL establish association only, not behavioral satisfaction or proof that unmapped behavior is absent.

## Capabilities

### New Capabilities

- `requirements-decision-context-runtime`: preserve optional requirement decision context.

### Modified Capabilities

None in this proposal. Existing lean reconciliation and optional assurance retain their own ownership.

## Impact

Planning only in this PR; no runtime, registry, manifest or version changes. Modules owns explicit native source extraction, source links and independent Requirements context presentation. It consumes released core records/digest and does not execute verification inside R09.

At implementation, update owning command help, adapter/reference and workflow guides on modules.specfact.io, README entry points where needed, frontmatter and navigation for added pages. Additive APIs remain optional; offline parsing/verification remains available. Rollback restores the prior compatible signed core/module pair and disables optional integration without rewriting historical reports.

## Dependencies and delivery

Depends on released paired core decision-context contract. #483 integration of optional context waits for a compatible signed context producer only when selected; absence does not block its ordinary path.

Implementation follows specification, derived tests, meaningful failing-before evidence, code, passing evidence and scope-appropriate gates. Use current repository reality and live issue readiness before work; do not interpret this planning approval as authority to bypass an In Progress owner or signed release gate.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#491](https://github.com/nold-ai/specfact-cli-modules/issues/491)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/491>
- **Repository**: `nold-ai/specfact-cli-modules`
- **Parent Feature**: #161
- **Last Synced Status**: planning / Todo, 2026-10-04

## Research boundary

The roadmap and sources are in [AGENTIC_SDLC_ROADMAP.md](../../AGENTIC_SDLC_ROADMAP.md). Product priority is an owner decision. Productivity, savings, complete hidden-behavior detection and universal independent reviewer recall are not established claims.

- **Paired Core Story**: [nold-ai/specfact-cli#750](https://github.com/nold-ai/specfact-cli/issues/750)

## Planning validation

See [AGENTIC_SDLC_VALIDATION.md](../../AGENTIC_SDLC_VALIDATION.md) for actual proposal checks and the explicit Python-only analyzer applicability exception. Runtime review and release tasks remain pending.
