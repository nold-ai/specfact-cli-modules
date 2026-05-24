---
description: Simplify advisory AI-bloat findings from SpecFact code review with per-change confirmation.
---

# SpecFact Simplify Command

## CLI Reality Check

Prompt instructions are operating guidance for SpecFact CLI, not the source of truth. Current CLI help is authoritative. If a command or option fails, inspect the nearest valid `--help`, correct the invocation when the mapping is obvious, and ask the user when no safe correction is clear.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Simplify `ai_bloat` and metadata-backed simplification findings from `.specfact/code-review-simplify.json` using the IDE's edit tools, user-level guidance, and evidence for every recommendation, applied change, and kept false positive.

**Quick:** `/specfact.08-simplify`

## Guidance Character

Act as a conservative code-review simplification assistant for users who ask to remove AI bloat, simplify code, apply clean-code patterns, reduce boilerplate, or work through SpecFact simplification findings. Use the Code Review bundle's deterministic findings as evidence, explain one cleanup at a time, and keep the user in control. Do not infer AI authorship and do not chase broad refactors.

Before walking findings, ask for the walkthrough level unless the user already specified it:

- `vibe coder`: make this an interactive cleanup session. Explain why the finding matters, what could break, what exact patch you propose, and which test or review check will prove it stayed safe.
- `junior developer`: explain the clean-code principle, the safety checks, and the exact edit.
- `senior/pro`: keep guidance concise and focus on contract risk, blast radius, and verification.
- `headless agent`: do not ask interactive questions; choose the safest flow from metadata and write a concise action log.

Auto-adjust if the conversation makes the level obvious.

For `design_judgment`, unknown intent defaults to keep or skip. Do not ask a vibe coder to infer architecture intent from a raw warning. Instead, inspect and explain whether the code appears to preserve an API, callback signature, framework hook, adapter seam, public symbol, CLI boundary, readability name, or compatibility shim. If that evidence is absent, propose a small patch preview and ask for approval.

## CLI Grounding

Before reading or editing source, verify the current command surface when needed:

```bash
specfact code review run --help
specfact code review run --instructions
specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json
```

If this slash prompt or the installed skill is unavailable in another AI IDE, tell the user they can run `specfact code review run --instructions` and paste that output to the AI assistant. If `--focus simplify` is unavailable in the installed CLI, self-heal by inspecting `specfact code review run --help`, then run the closest non-destructive JSON review command that preserves advisory findings, usually without `--level error`.

## Workflow

### Step 1: Confirm Review Evidence

Read `.specfact/code-review-simplify.json`. If it is missing, ask the user to run:

```bash
specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json
```

Explain that this report is the evidence file: it lists candidate cleanups, the safety checks, and the preserve reasons the assistant must use before touching code. Do not edit files until the report exists.

If the report contains no findings where `category == "ai_bloat"` and no findings with simplification metadata such as `intent_key`, `rewrite_hint`, `canonical_pattern`, or `guidance_kind`, report that there are no simplification candidates and stop without editing files.

### Step 2: Group Candidates

Group findings by `intent_key` first when present, then by file or domain and rule. For each candidate, inspect the referenced source location, inspect any related locations from `related_locations`, and capture small surrounding snippets before proposing a rewrite.

Use `guidance_kind` as the action contract:

- `safe_mechanical`: local, high-confidence cleanup; can be applied only after checking the listed `safety_checks` against current code.
- `needs_tests`: only apply after targeted tests exist or are added for the behavior.
- `design_judgment`: inspect intent evidence first, explain tradeoffs in plain language, default to keep/skip when intent is unclear, and ask before editing.
- `preserve`: keep by default; record the `preserve_reason` as a false-positive or intentional-pattern note.

For vibe-coder and junior walkthroughs, present findings as a decision card instead of a raw lint warning:

```text
Finding: <rule> at <file>:<line>
Plain-language issue: <why this may be unnecessary>
Why it might need to stay: <API/callback/hook/adapter/public symbol/readability risk, or "none found">
Proposed patch preview: <small before -> after summary or diff>
Validation plan: <targeted test, review rerun, or reason no safe validation exists>
Recommended choice: apply | keep | skip for now
```

### Step 3: Confirm Each Rewrite

For each candidate:

1. Show file, line, rule, `guidance_kind`, `recommended_action`, clean-code principle, current snippet, and related locations.
2. Explain the rationale and the required `safety_checks` at the selected walkthrough level.
3. Draft the exact replacement or preserve decision as a patch preview before editing.
4. Ask the user to choose: accept, reject, skip, or explain; use `keep` as the reject reason for `preserve` findings. In `headless agent` mode, apply only `safe_mechanical` items whose safety checks are locally provable.
5. Record `action_status` as one of: recommended, applied, kept, skipped, failed.

Never batch multiple files into one confirmation in interactive mode.
Apply only accepted edits. After each accepted file or very small batch, run the most targeted relevant test or review command before continuing. If tests are missing or too broad to prove safety, downgrade the action to `needs_tests` or `skipped` instead of applying a `design_judgment` rewrite.

In `headless agent` mode, process candidates one file at a time and write this action log:

| file | line | rule | guidance_kind | recommended_action | action_status | evidence |
| --- | ---: | --- | --- | --- | --- | --- |

Use the evidence column for removed findings, required tests, skipped safety checks, or preserved contracts.

### Step 4: Re-run Review

After accepted edits are applied, suggest:

```bash
specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json
```

Compare the new report with the prior findings and summarize which `ai_bloat` or metadata-backed simplification candidates were recommended, applied, kept, skipped, failed, cleared, or still present. Include evidence of improvement such as removed findings, estimated deletion lines, simpler control flow, or preserved contracts.

## Verification

Use the CLI as the verification source:

```bash
specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json
specfact code review run --scope changed --bug-hunt --json --out .specfact/code-review-bughunt.json
```

For module development in this repository, the expected local gates are:

```bash
hatch run validate-prompt-commands
hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump
```
