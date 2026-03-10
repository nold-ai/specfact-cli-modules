# Design: Fix HTML parsing and export validation

## Context

`specfact backlog daily --summarize --comments --copilot-export` can raise exceptions when processing ADO work item comments containing rich HTML (inline styles, nested divs, embedded images). Code review identified issues in `specfact-cli-modules/packages/specfact-backlog/src/specfact_backlog/backlog/commands.py`.

## Goals / Non-Goals

**Goals:**
- Fix asymmetry between `--copilot-export` and `--summarize` comment normalization
- Add defensive error handling for malformed HTML
- Mitigate ReDoS risk on long input
- Ensure export never aborts on edge cases

**Non-Goals:**
- Re-implement HTML parsing from scratch
- Change Markdown output format
- Add new features beyond hardening

## Decisions

### 1. Copilot Export Normalization

**Decision**: Apply `_normalize_markdown_text` to comments in `_build_copilot_export_content`.

**Rationale**: Currently only `_build_summarize_prompt_content` normalizes comments. Copilot export writes raw HTML which breaks downstream consumers. Fixing this aligns both outputs.

### 2. Exception Handling

**Decision**: Wrap `_normalize_markdown_text` in try/except with fallback.

**Rationale**: The `@ensure` postcondition raises `ViolationError` when HTML tags remain. This should not abort the entire export.

**Fallback implementation:**
```python
try:
    normalized = _normalize_markdown_text(text)
except Exception:
    # Fallback: strip tags, unescape entities
    normalized = re.sub(r"<[^>]+>", "", html.unescape(str(text)))
```

### 3. ReDoS Mitigation

**Decision**: Add input length guard before regex processing.

**Rationale**: Patterns like `[^>]*` can backtrack catastrophically on long attributes (e.g. base64 images).

**Guard implementation:**
```python
MAX_INPUT_LEN = 50 * 1024  # 50KB
if len(text) > MAX_INPUT_LEN:
    text = text[:MAX_INPUT_LEN] + "\n... [truncated]"
```

### 4. Defensive Typing

**Decision**: Add `str()` coercion for comment values.

**Rationale**: ADO API may return non-string types in edge cases. This prevents `TypeError` during normalization.

## Implementation Sequence

1. Add `_normalize_markdown_text` to copilot export comment loop
2. Add input length guard at start of `_normalize_markdown_text`
3. Wrap normalization in try/except with fallback
4. Add defensive `str(c)` when iterating comments
5. Write tests proving edge cases are handled
6. Run quality gates
