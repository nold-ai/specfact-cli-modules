## Context

The current CLI help surface in this workspace exposes the following mounted groups:

- Core: `init`, `module`, `upgrade`
- Installed bundle roots: `backlog`, `code`, `govern`, `project`, `spec`
- Nested groups used by current docs examples:
  - `project sync`
  - `code analyze`
  - `code drift`
  - `code review`
  - `code validate`
  - `code repro`
  - `govern enforce`

The bundle manifests in this repository publish official package ids under the `nold-ai/...` namespace.

## Decisions

- Treat live `hatch run specfact --help` output as the source of truth for mounted command paths.
- Update central reference and installation pages first, because they drive most user navigation and copy-paste behavior.
- Use fully qualified official module ids such as `nold-ai/specfact-backlog` in docs examples to avoid stale namespace assumptions.
- Avoid inventing replacements for command groups that are not currently mounted; instead, remove or stop advertising them from the central docs.

## Verification

- Re-run targeted `hatch run specfact ... --help` commands for the paths documented after the edits.
- Re-run `rg` searches for the old command prefixes in the edited files to confirm the stale references were removed there.
