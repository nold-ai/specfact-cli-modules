## Why

`specfact-cli-modules` still uses a thin pre-commit setup compared to `specfact-cli`. That lets formatting drift, missing bundle-signature verification, and other quality regressions reach CI instead of failing locally before commit.

## What Changes

- Align the modules-repo pre-commit configuration with the quality gates that matter in day-to-day development.
- Add a consolidated local pre-commit script that enforces signature/version checks, formatter safety, and modules-repo quality checks before commit.
- Keep the hook behavior pragmatic for the modules repo by using staged-file aware checks and the existing `contract-test`/`smart-test` entrypoints.

## Capabilities

### New Capabilities
- `modules-pre-commit-quality-parity`: Local commits in `specfact-cli-modules` fail early when bundle signatures are stale, formatting would change files, or required repo quality checks fail.

## Impact

- Affected code: `.pre-commit-config.yaml`, new pre-commit helper script, workflow tests.
- Affected systems: local developer commits in `specfact-cli-modules`.
