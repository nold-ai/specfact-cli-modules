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

Use the Code Review bundle to detect bloat patterns commonly produced by AI-assisted coding, then use the Project bundle's `/specfact.08-simplify` prompt to review each cleanup with confirmation.

## 1. Install and refresh prompts

```bash
specfact module install nold-ai/specfact-code-review
specfact module install nold-ai/specfact-project
specfact init ide
```

## 2. Run review with full JSON evidence

```bash
specfact code review run --json --out .specfact/code-review.json
```

Omit `--level` for this report. `--level error` intentionally filters info-level findings, including `ai_bloat`, out of the command output.

## 3. Inspect the signal

Look for findings where `category` is `ai_bloat`. They are `severity=info`, advisory-only, and score-neutral.

In the implementation dry run for this change, the AST detector found 144 advisory `ai_bloat` candidates across `specfact-code-review` and `specfact-project` package sources. No automatic rewrites were applied, so the measured accepted-rewrite LOC delta was 0; `/specfact.08-simplify` is the human-confirmed rewrite path.

```json
{
  "category": "ai_bloat",
  "severity": "info",
  "rule": "ai-bloat.identity-try-except"
}
```

## 4. Simplify in the IDE

Run `/specfact.08-simplify`. The prompt reads `.specfact/code-review.json`, groups findings by file and rule, and asks before applying each edit.

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
specfact code review run --json --out .specfact/code-review.json
```

Use the new report to confirm accepted simplifications cleared the corresponding `ai_bloat` findings. This is bloat-shape detection, not AI-authorship detection.
