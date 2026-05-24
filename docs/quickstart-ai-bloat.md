---
layout: default
title: AI bloat quickstart
nav_order: 6
permalink: /quickstart-ai-bloat/
keywords: [code-review, ai-bloat, simplify, ai-ide]
audience: [solo, team, enterprise]
expertise_level: [beginner, intermediate]
---

# AI bloat quickstart

Use the Code Review bundle to detect bloat patterns commonly produced by AI-assisted coding, estimate cleanup impact, and hand structured remediation packets to any AI IDE. The Project bundle's `/specfact.08-simplify` prompt can still drive the confirmed rewrite loop.

## 1. Install and refresh prompts

```bash
specfact module install nold-ai/specfact-code-review
specfact module install nold-ai/specfact-project
specfact init ide
```

## 2. Run simplify review with cleanup forecast evidence

```bash
specfact code review run --scope changed --focus simplify --preview-fixes --json --out .specfact/code-review-simplify.json
```

Omit `--level` for this report. `--level error` intentionally filters info-level findings, including `ai_bloat`, out of the command output. `--preview-fixes` is non-mutating: it adds patch forecast evidence without editing tracked files.

## 3. Inspect the signal

Look first at `cleanup_forecast`. It summarizes reviewed LOC, low/expected/high deletion estimates, guidance-kind totals, AI-bloat density, weighted bloat points, and cleanup-yield LOC per KLOC. Then inspect findings where `category` is `ai_bloat`. They are `severity=info`, advisory-only, and score-neutral.

Example output from the implementation dry run for this change: the AST detector found advisory `ai_bloat` candidates across `specfact-code-review` and `specfact-project` package sources, with no automatic rewrites applied. `/specfact.08-simplify` is the human-confirmed rewrite path.

```json
{
  "category": "ai_bloat",
  "severity": "info",
  "rule": "ai-bloat.identity-try-except",
  "guidance_kind": "safe_mechanical",
  "remediation_packet": {
    "safe_to_autofix": true,
    "validation_plan": ["run targeted tests", "rerun simplify review"]
  }
}
```

## 4. Simplify in the IDE

Run `/specfact.08-simplify` or pass `.specfact/code-review-simplify.json` to your AI IDE. The JSON is the contract: sort by `guidance_kind`, use each `remediation_packet`, preserve anything with `preserve_reasons`, and ask before editing `design_judgment` findings.

Example cleanup:

```python
def parse(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise
```

becomes:

```python
def parse(raw: str) -> int:
    return int(raw)
```

Another common cleanup:

```python
def double(values: list[int]) -> list[int]:
    result = []
    for value in values:
        result.append(value * 2)
    return result
```

becomes:

```python
def double(values: list[int]) -> list[int]:
    return [value * 2 for value in values]
```

## 5. Re-run review

```bash
specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json
```

Use the new report to confirm accepted simplifications cleared the corresponding `ai_bloat` findings. This is bloat-shape detection, not AI-authorship detection.
