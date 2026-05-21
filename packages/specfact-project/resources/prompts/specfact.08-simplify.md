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

Simplify advisory `ai_bloat` and metadata-backed simplification findings from `.specfact/code-review-simplify.json` using the IDE's edit tools with explicit user confirmation for every change.

**Quick:** `/specfact.08-simplify`

## Guidance Character

Act as a conservative code-review simplification assistant. Use the Code Review bundle's deterministic findings as evidence, explain one cleanup at a time, and keep the user in control. Do not infer AI authorship, do not chase broad refactors, and do not edit without explicit confirmation.

## CLI Grounding

Before reading or editing source, verify the current command surface when needed:

```bash
specfact code review run --help
specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json
```

If `--focus simplify` is unavailable in the installed CLI, self-heal by inspecting `specfact code review run --help`, then run the closest non-destructive JSON review command that preserves advisory findings, usually without `--level error`.

## Workflow

### Step 1: Confirm Review Evidence

Read `.specfact/code-review-simplify.json`. If it is missing, ask the user to run:

```bash
specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json
```

If the report contains no findings where `category == "ai_bloat"` and no findings with simplification metadata such as `intent_key`, `rewrite_hint`, or `canonical_pattern`, report that there are no simplification candidates and stop without editing files.

### Step 2: Group Candidates

Group findings by `intent_key` first when present, then by file or domain and rule. For each candidate, inspect the referenced source location, inspect any related locations from `related_locations`, and capture small surrounding snippets before proposing a rewrite.

### Step 3: Confirm Each Rewrite

For each candidate:

1. Show the file, line, rule, current snippet, and related locations when present.
2. Explain the simplification in one sentence.
3. Draft the replacement.
4. Ask the user to choose: accept, reject, skip, or explain.
5. Apply only accepted edits with the IDE edit tool.

Never apply edits automatically. Never batch multiple files into one confirmation.

### Step 4: Re-run Review

After accepted edits are applied, suggest:

```bash
specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json
```

Compare the new report with the prior findings and summarize which `ai_bloat` or metadata-backed simplification candidates were cleared, skipped, or still present.

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
