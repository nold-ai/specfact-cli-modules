## Context

This change owns the executable half of deterministic pre-implementation assurance. It consumes the core contract from `preflight-01-design-contract-core` and keeps workflow prose thin by placing determinate checks in Python validators.

The integration research reviewed on 2026-08-25 supports a canonical-skill plus adapter model:

- OpenSpec generates harness-appropriate forms for the same command intent: <https://github.com/Fission-AI/OpenSpec/blob/main/docs/commands.md>
- Spec Kit exposes ordered pre-implementation clarification and analysis gates while invocation syntax varies by agent: <https://github.github.com/spec-kit/reference/agentic-sdd.html>
- ECC documents skills-first workflow ownership and command shims only when compatibility requires them: <https://github.com/affaan-m/everything-claude-code/blob/main/.agents/skills/everything-claude-code/SKILL.md>
- hatch3r generates supported platform adapters from canonical packaged content and inventory: <https://github.com/hatch3r/hatch3r>

## Goals / Non-Goals

**Goals:**

- Provide one deterministic pre-implementation loop for existing and new OpenSpec changes.
- Let a human see and refine blocking findings before any implementation work starts.
- Produce machine-readable and human-readable results from the same validator output.
- Ship canonical workflow content with the future module so generic installers and harness adapters can consume it later.

**Non-Goals:**

- Publish or sign the module in this change.
- Generate harness-specific files or edit project AGENTS.md.
- Implement worktree/index checkpoints or final range conformance.
- Let prompts decide structural readiness independently of Python validators.

## Decisions

### 1. Canonical loop and stop states

The runtime state machine is `DISCOVER -> SNAPSHOT -> VALIDATE -> REVIEW`. A user may then choose `REFINE`, `APPROVE`, or `STOP`. Refinement changes are never automatic: the workflow presents proposed source-owned edits, requires user authorization, returns to `SNAPSHOT`, and reruns every required validator. `APPROVE` is available only for a determinate ready result and produces a seal. Any blocking or unknown result stops implementation.

### 2. Read-only default and explicit persistence

`specfact preflight run <change-id>` is read-only by default. `--write` may persist normalized artifacts only after the user confirms exact target paths. The planned project-local layout is `.specfact/preflight/<change-id>/` with a contract, validation result, and approval seal. Final filenames and schemas are derived from the core contract tests before implementation. Any authorized refinement of a user-owned artifact routes through its owning workflow and the paired core safe-write contract, checks the expected source identity before commit, and preserves unrelated content rather than replacing the file wholesale.

### 3. Python validator registry

Validators are Python implementations registered under stable IDs and versions. The initial required set covers:

- required OpenSpec artifact and scenario completeness;
- source identity/freshness and repository-state capture;
- request-to-scope and task-to-requirement traceability;
- dependency graph completeness, native GitHub metadata, cycles, and readiness;
- interface ownership and cross-repository counterpart consistency;
- role-classified implementation paths and explicit exclusions;
- component ownership with bounded pytest targets;
- every closed core risk dimension (`boundary`, `malformed_or_missing_input`, `state_transition`, `idempotency`, `cache`, `error`, `status`, `timeout`, `unknown_precedence`, `path`, `repository_lifecycle`, `platform`, and `compatibility`) marked `covered` or `not_applicable`, with rationale where not applicable;
- covered risk rows mapped at `planned` maturity to existing Requirements requirement/scenario/case identities, method, intent, observable, and touchpoints without fabricating selectors;
- test-authored refinement that reconciles the Requirements-owned exact pytest selector to the same planned case, requires explicit successor-seal approval before production implementation, and preserves the original implementation-lineage baseline;
- earliest execution stage from `slice`, `commit`, `prepush`, or `ci`;
- acceptance criteria, failing-first plan, rollback, and non-goals;
- active-issue/worktree collision and planning-only boundary checks.

Validators return structured findings only. Rendering, policy aggregation, and persistence consume those results.

### 4. Skill delegates, never reimplements

The module-owned `specfact-preflight` skill defines when to invoke the runtime, how to present findings, how to request approval for refinement, and when to stop. Harness-specific aliases may spell it `/specfact-preflight`, `$specfact-preflight`, or another native form. The workflow must run the CLI and consume its JSON; it may not recreate checks in prose.

### 5. Instruction layering

General AGENTS.md/OpenSpec/Spec Kit instructions should contain only the gate: select a change, run the installed preflight workflow, require a valid current seal, and stop on blocking/unknown/stale results. Detailed loop content remains in the module-owned skill. Core #251 later discovers/installs/exports that skill, and core #253 later generates the small harness instruction reference.

### 6. Assurance language

`READY` means the configured deterministic checks completed for the exact captured inputs and a human may approve that reviewed contract. It does not mean the design is optimal or the future code is correct.

## Risks / Trade-offs

- **Prompt/runtime divergence:** Version the skill contract with the module and test that it invokes only supported CLI forms.
- **Accidental artifact edits during review:** Default to read-only and require explicit target confirmation, source-owner routing, conflict detection, and preservation of unrelated user content.
- **False-ready result from missing validators:** Required validator absence yields `UNKNOWN`, never success.
- **Cross-repository race:** Capture repository refs and GitHub identities; stale identities invalidate approval.
- **False semantic coverage:** Missing component ownership, unresolved risk disposition, or stale Requirements plan identity is blocking or `UNKNOWN`, never inferred ready.
- **Duplicate selector ownership:** Reuse the existing Requirements maturity lifecycle: seal complete planned cases without selectors, then validate Requirements-owned exact selectors at test-authored maturity rather than creating a preflight-specific selector grammar.

## Migration and Rollback

The first implementation remains unpublished and dogfood-only. Repositories without the module continue their existing OpenSpec process. Before stable publication, rollback is removal of the opt-in module and its project-local `.specfact/preflight/` artifacts.

## Open Questions Deferred to Implementation

- Exact names for renderer subcommands and non-interactive approval import.
- Whether optional policy profiles may add validators without changing the base readiness semantics.
- Retention and redaction defaults for persisted source excerpts.
