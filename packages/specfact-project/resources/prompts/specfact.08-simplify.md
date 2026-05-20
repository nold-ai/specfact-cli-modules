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

Simplify advisory `ai_bloat` findings from `.specfact/code-review.json` using the IDE's edit tools with explicit user confirmation for every change.

**Quick:** `/specfact.08-simplify`

## Workflow

### Step 1: Confirm Review Evidence

Read `.specfact/code-review.json`. If it is missing, ask the user to run:

```bash
specfact code review run --json --out .specfact/code-review.json
```

If the report contains no findings where `category == "ai_bloat"`, report that there are no ai-bloat candidates and stop without editing files.

### Step 2: Group Candidates

Group findings by file, then by rule. For each candidate, inspect the referenced source location and capture a small surrounding snippet before proposing a rewrite.

### Step 3: Confirm Each Rewrite

For each candidate:

1. Show the file, line, rule, and current snippet.
2. Explain the simplification in one sentence.
3. Draft the replacement.
4. Ask the user to choose: accept, reject, skip, or explain.
5. Apply only accepted edits with the IDE edit tool.

Never apply edits automatically. Never batch multiple files into one confirmation.

### Step 4: Re-run Review

After accepted edits are applied, suggest:

```bash
specfact code review run --json --out .specfact/code-review.json
```

Compare the new report with the prior findings and summarize which `ai_bloat` candidates were cleared, skipped, or still present.
