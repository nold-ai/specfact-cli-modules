## Why

The modules docs still describe pre-reorganization command paths and old bundle identifiers in several core reference and installation pages. Readers following those pages hit commands that are no longer mounted in the current CLI or install the wrong module ids.

## What Changes

- Audit the current mounted CLI surface against the modules docs using live `specfact --help` output and module manifests.
- Update core reference and getting-started pages to use the current mounted command paths such as `specfact project sync ...`, `specfact code repro ...`, `specfact govern enforce ...`, and `specfact code validate ...`.
- Replace stale example module identifiers like `specfact/backlog` and `backlog-core` with the official `nold-ai/...` package ids shipped from this repository.
- Add a docs requirement that modules docs must reflect the current mounted command surface and official bundle ids.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `modules-docs-publishing`: Docs command examples and install guidance must match the current mounted CLI surface and official module ids.

## Impact

- Affected docs under `docs/reference/`, `docs/guides/`, and `docs/getting-started/`
- OpenSpec delta under `openspec/changes/docs-cli-command-alignment/specs/modules-docs-publishing/spec.md`
- User-facing impact: readers can follow current commands without falling back to removed shims or obsolete package ids
