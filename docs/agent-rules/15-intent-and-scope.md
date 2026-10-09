---
layout: default
title: Agent intent and scope decisions
permalink: /contributing/agent-rules/intent-and-scope/
description: Ask-decide-challenge checkpoints that bind architecture, effort, and acceptance to the user's actual workflow.
keywords: [agents, intent, scope, decisions, cost, architecture]
audience: [team, enterprise]
expertise_level: [advanced]
doc_owner: specfact-cli-modules
tracks:
  - AGENTS.md
  - docs/agent-rules/**
last_reviewed: 2026-10-05
exempt: false
exempt_reason: ""
id: agent-rules-intent-and-scope
always_load: true
applies_when:
  - session-bootstrap
  - implementation
  - openspec-change-selection
  - change-readiness
  - verification
priority: 15
blocking: true
user_interaction_required: true
stop_conditions:
  - consequential use case or trust assumption unconfirmed
  - material scope expansion without an explicit decision
  - agreed effort limit reached
depends_on:
  - agent-rules-index
  - agent-rules-non-negotiable-checklist
---

# Agent intent and scope decisions

Apply **ask -> decide -> challenge** before architecture, specification expansion,
or implementation. The purpose is to prevent expensive work toward an assumed
problem. Read-only exploration and independent work may continue while a required
answer is pending. Routine, reversible implementation choices within confirmed
scope do not require another approval.

## Ask: establish the actual workflow

Reuse explicit user answers and constraints already in the session. For a change
with architectural choices, record:

- **User and outcome:** who needs this, the problem today, and one concrete example
  of the desired invocation and result.
- **Inputs and trust:** whose code and data are processed, which code executes,
  and which assets need protection. Separate repository integrity, dependency
  separation, reproducibility, and hostile-code containment.
- **Environment and constraints:** required OS/architecture, installation route,
  permissions, dependencies, and restrictions on paid accounts or services.
- **Non-goals:** excluded workflows, platforms, adversaries, and optional hardening.
- **Done:** observable end-to-end acceptance on a representative user project,
  plus the existing applicable security, quality, and release gates.
- **Effort:** a bounded first milestone and any user-supplied time, spending,
  token, or agent limits. State when reliable cost telemetry is unavailable.

If a missing answer could materially change security architecture, compatibility,
cost, or acceptance, ask one concise bundled clarifier that explains the consequence
and offers a recommendation. Do not turn speculation into a requirement. An
unanswered question or generic "go ahead" does not confirm an unstated threat model.
If the user explicitly delegates the choice, record that delegation and its bounds.
For a small documentation or reversible fix with clear intent, a short scope note
is sufficient; do not invent a new planning project.

## Decide: choose the smallest sufficient design

Before committing to custom infrastructure, compare existing capability/reuse,
a minimal adaptation, and a custom design. A brief comparison is sufficient:
user benefit, constraints met, compatibility impact, implementation effort,
maintenance burden, and uncertainty. Avoid unsupported monetary estimates.

- Recommend the least complex option that meets the confirmed outcome and
  mandatory constraints. Explain why any simpler option is insufficient.
- Label requirements as user-confirmed, externally mandatory with a source,
  engineering recommendations, or unresolved assumptions. Recommendations become
  delivery blockers only through an explicit scope decision.
- Write the decision into the change's proposal/design when applicable; record
  the source of consequential answers, selected option, alternatives, non-goals,
  first milestone, and acceptance. Use a concise session note for documentation work.
- Approval is useful only after the user can see the tradeoffs and what is excluded.
  Do not treat approval of an agent-authored plan as independent evidence for its
  assumptions. Existing explicit authorization remains valid within its scope.
- Implement one complete vertical slice on a representative project before
  generalizing adapters, catalogs, orchestration, platform matrices, or release
  infrastructure. Dependency prerequisites must be justified by that slice.

## Challenge: interrupt drift before it becomes expensive

Reopen the decision when new evidence introduces a different use case or adversary,
a new platform, custom broker/daemon/service, paid distribution prerequisite,
stricter acceptance, incompatible project behavior, or a material effort increase.

State the original outcome, the new evidence, the proposed scope/effort change,
the simplest viable alternative, and a recommendation. Obtain a decision before
performing work that depends on a material expansion. Continue independent fixes
within authorized scope. User-approved effort limits are stop conditions.

- Security findings require triage against the confirmed trust assumptions and
  assets. A plausible hostile scenario alone does not establish customer need.
  Genuine applicable vulnerabilities still require correction.
- Do not weaken existing security, tests, budgets, or acceptance to make a gate
  pass. A scope revision must be explicit, record affected guarantees, and update
  specifications and acceptance together before dependent implementation.
- After two consecutive attempts at the same failed gate without changed inputs
  or new evidence, stop repeating it. Diagnose the cause and report the concrete
  blocker and next evidence needed. Resume the gate when something relevant changes.
- Default to no subagents. Where authorized, use bounded tasks and reuse existing
  workers; state the purpose and maximum concurrency before delegation. Do not
  recursively fan out or create replacement agents for unchanged blockers.
- At each milestone, report the user workflow demonstrated, remaining blockers,
  effort consumed when measurable, and the next bounded step. CI, review activity,
  token volume, and elapsed calendar days do not establish delivered value or
  equivalent human labor.

## Review and completion

Check the implementation against the recorded user example and non-goals. If a
representative project cannot complete that workflow, report partial delivery and
the failing step. Distinguish implemented logic, executed acceptance, available
artifacts, and published support. Green component tests cannot substitute for the
agreed end-to-end outcome. Reassess value and remaining effort before continuing
past a failed milestone.

## Example: native review of a developer's own repository

"Run review on my Mac without changing my project" establishes a workflow to
clarify. Ask whether the inputs are the developer's own repositories or arbitrary
untrusted contributions, whether tests/build hooks execute, and which protections
are required. Dependency separation and an unchanged checkout do not imply a
hostile-code threat model. Conversely, trusted inputs do not remove applicable
existing security gates. Record the decision before choosing a custom sandbox
architecture, and first demonstrate the requested review on a representative
supported developer-owned project without modifying its checkout or environment.
