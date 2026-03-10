## Why

The modules repo quality gates are currently reading backlog bundle code from the installed `~/.specfact/modules` copy instead of the local workspace in some test paths. That makes the branch fail against stale code even when the local backlog fixes are present.

## What Changes

- Ensure modules-repo tests and local quality gates prefer the checked-out bundle sources over installed user-home bundle copies.
- Add regression coverage so backlog bundle tests fail if they resolve from an external installed bundle instead of the local workspace.
- Restore green contract/smart test runs for the combined backlog and registry-publish PR state.

## Capabilities

### New Capabilities
- `local-bundle-test-alignment`: Tests and local gate runs resolve backlog bundle imports from the workspace under test, not from stale installed bundle copies.

### Modified Capabilities

## Impact

- Affected code: test bootstrap/import path handling and bundle-local regression tests.
- Affected systems: `hatch run contract-test`, `hatch run smart-test`, and local pytest resolution.
