# Change: Fix HTML parsing and export validation in backlog daily

## Why

`specfact backlog daily --summarize --comments --copilot-export` can raise exceptions when processing ADO work item comments that contain rich HTML (inline styles, nested divs, embedded images). Code review identified:

1. **Asymmetry**: `--copilot-export` writes comments raw (no normalization) while `--summarize` normalizes them. Copilot export can contain raw HTML that breaks downstream parsing.
2. **ReDoS risk**: Regex patterns with `[^>]*` can cause catastrophic backtracking on long attribute values (e.g. base64 images, long style attributes).
3. **icontract @ensure**: If normalization fails to strip all tags, the postcondition raises and aborts the entire export.
4. **No defensive fallback**: Malformed HTML or edge cases cause unhandled exceptions instead of graceful degradation.

## What Changes

- Apply `_normalize_markdown_text` to comments in `_build_copilot_export_content` (fix asymmetry with summarize).
- Add try/except around `_normalize_markdown_text` with fallback to stripped plain text so export does not abort on edge cases.
- Add input length guard (e.g. truncate or reject inputs > 50KB) before regex processing to mitigate ReDoS.
- Add defensive `str()` coercion for comment values to handle unexpected API response types.

## Capabilities

### Modified Capabilities

- `backlog-daily-markdown-normalization`: Extend to cover `--copilot-export` output; harden `_normalize_markdown_text` against ReDoS and edge cases; add fallback so export never aborts on malformed HTML.

### Impact

- **User-facing**: `specfact backlog daily --copilot-export --comments` will produce Markdown-only output (no raw HTML) and will not raise on complex ADO comments.
- **Docs**: Update backlog-guide or agile-scrum-workflows if export behavior is documented.

## Dependencies

- `backlog-scrum-05-summarize-markdown-output` (archived) established the normalization spec.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli -->
- **GitHub Issue**: TBD
- **Last Synced Status**: proposed
