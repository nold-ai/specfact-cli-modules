# backlog-daily-markdown-normalization Specification

## Purpose
TBD - created by archiving change bugfix-backlog-html-export-validation. Update Purpose after archive.
## Requirements
### Requirement: Copilot export SHALL normalize comments identically to summarize

The system SHALL apply the same HTML-to-Markdown normalization used for `--summarize` and `--summarize-to` to `--copilot-export` output when `--comments` is enabled.

#### Scenario: Copilot export with comments contains no raw HTML
- **WHEN** the user runs `specfact backlog daily --copilot-export <path> --comments` with work items whose comments contain HTML (e.g. ADO rich content)
- **THEN** the exported file contains only Markdown-formatted text in the per-item comment sections
- **AND** no raw HTML tags or un-decoded HTML entities appear in the export

### Requirement: Normalization SHALL not abort export on malformed or edge-case input

The system SHALL handle malformed HTML, very long input, and unexpected types without raising unhandled exceptions.

#### Scenario: Malformed HTML does not abort export
- **WHEN** a comment contains malformed HTML (e.g. `<div` without closing `>`)
- **THEN** the normalization returns stripped plain text (tags removed, entities unescaped)
- **AND** the export completes successfully

#### Scenario: Very long input does not cause ReDoS
- **WHEN** a comment or description exceeds a configurable length threshold (e.g. 50KB)
- **THEN** the system truncates or skips regex-heavy processing before normalization
- **AND** the export completes within reasonable time

#### Scenario: Non-string comment values are handled defensively
- **WHEN** the adapter returns a comment value that is not a string (e.g. dict, None)
- **THEN** the system coerces to string before normalization
- **AND** the export does not raise TypeError

