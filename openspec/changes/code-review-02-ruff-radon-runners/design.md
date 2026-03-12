# Design: code-review Ruff and Radon runners

## Runner pattern

Both runners follow the same contract:

1. Accept `files: list[Path]`
2. Short-circuit to `[]` when no files are provided
3. Invoke the external tool with JSON output for only the provided files
4. Parse tool output into `ReviewFinding` instances
5. Convert parse or tool-availability failures into a single `tool_error` finding

`@require`, `@ensure`, and `@beartype` are used so the new helpers match the existing
bundle conventions around runtime contracts.

## Ruff mapping

`ruff check --output-format json` returns per-finding JSON entries. The bundle maps
rule prefixes as follows:

- `S*` -> `security`
- `C9*` -> `clean_code`
- `E*`, `F*`, `I*`, `W*` -> `style`

The runner treats a non-empty `fix` payload as `fixable=True`. Findings are filtered to
the provided file set even if mocked tool output contains extra files. Unsupported rule
families are skipped so the bundle only emits governed categories it explicitly maps.

## Radon mapping

`radon cc -j` returns a JSON object keyed by file path. Each block with complexity above
12 becomes a finding:

- complexity `13..15` -> `severity="warning"`
- complexity `>15` -> `severity="error"`

Complexity `<=12` does not emit a finding. All radon findings map to
`category="clean_code"`. The default Hatch environment also installs `radon` so the
runner works in the repo's normal dev and CI paths instead of immediately degrading to
`tool_error`.

## Error handling

`FileNotFoundError`, `subprocess.TimeoutExpired`, `OSError`, or invalid JSON produce one
`ReviewFinding(category="tool_error", ...)` instead of raising. This keeps review runs
resilient when an external tool is missing or returns malformed output.
