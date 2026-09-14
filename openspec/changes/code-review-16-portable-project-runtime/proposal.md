# Portable project runtimes for capsule review

## Why

Bug #472 reports external Hatch capsule reviews without the consumer dependency graph. Static inspection confirms the ordinary-review handoff gap and broad import/plugin restrictions. Reported customer counts are not independently reproduced: the original PR returns HTTP 404 to the implementation identity.

## What Changes

Automatically discover and prepare pip/pip-tools, Hatch, uv and Poetry runtime context; add inspect/prepare commands and project-config/project-runtime review options. Introduce local content-addressed project-runtime-layer-v2 without changing v1 authority. Isolate project workers, preserve dependency pins and native-library evidence, and retain static findings when dependent evidence is incomplete. Validate pinned real external repos and signed public installation.

## Capabilities

### New Capabilities

- `portable-project-runtime`: discovery, isolated preparation, descriptor validation, attachment and customer evidence.

### Modified Capabilities

- Code Review local and immutable scope execution, pytest inventory, import-domain preflight, and customer CI acceptance.

## Impact

Production changes remain in packages/specfact-code-review. New packaged runtime commands and contract resources require a minor bundle release (0.50.0 if available), signatures, registry/index.json and immutable resource identity updates. Update docs/modules/code-review.md at the existing modules.specfact.io reference permalink. Retain core compatibility unless actual contract tests establish a higher minimum.

## Tracking

User Story: https://github.com/nold-ai/specfact-cli-modules/issues/473
Bug: https://github.com/nold-ai/specfact-cli-modules/issues/472
Parent Feature #163, Epic #162; #472 is natively blocked by #473. Baseline context: #466, #459, #175. No open prerequisites. Implementation authorized 2026-09-14 Europe/Berlin on codex/feature-code-review-16-portable-project-runtime toward dev.
