## Context

The core repo already uses a staged-file aware shell hook that enforces signature verification and formatter safety before commit. The modules repo only runs a few direct `hatch` commands from pre-commit, so common failures show up in CI after the commit instead of locally.

## Decision

- Replace the thin multi-hook pre-commit setup with a local shell script modeled on the core repo flow.
- Keep a dedicated signature verification hook and add a consolidated modules quality hook.
- The modules quality hook will:
  - run formatter safety
  - run markdown/yaml/import-boundary checks when relevant
  - skip heavier tests for safe-only doc/version/workflow changes
  - otherwise run the modules repo `contract-test` fast path

## Validation

- Add tests that assert the pre-commit config exposes both signature verification and the modules quality hook.
- Add tests that assert the helper script contains the required gate commands.
- Run the targeted tests plus the standard repo quality checks touched by the change.
