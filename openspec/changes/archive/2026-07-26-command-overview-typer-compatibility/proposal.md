## Why

Docs Review installs Typer 0.27.0, whose command parameters no longer inherit
from Click's public option and argument classes. The command-overview generator
therefore emits empty metadata in CI and rejects the checked-in artifacts as
stale.

## What Changes

- Make command-parameter classification compatible with Typer 0.27.0 and the
  project's Click version.
- Add regression coverage for Typer-provided option and argument parameters.
- Regenerate the command overview artifacts using the CI dependency set.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `module-command-overview`: Generate deterministic option and argument
  metadata under the pinned Docs Review Typer runtime.

## Impact

- Affects `scripts/generate-command-overview.py`, its unit tests, and the
  generated `llms.txt` and command-reference artifacts.
- Does not change module manifests, registry entries, public command syntax,
  package versions, or signatures.
