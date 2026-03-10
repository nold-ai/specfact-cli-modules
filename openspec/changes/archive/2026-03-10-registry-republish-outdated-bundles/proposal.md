## Why

The current modules publish workflow only inspects bundle directories changed by the current push and only compares them to the checked-out branch's `registry/index.json`. That misses cases where a bundle manifest version is already ahead of the exposed registry and should trigger the existing auto publish PR even if the current diff did not touch that package again.

## What Changes

- Add a registry consistency capability that detects any bundle manifest version newer than the registry entry selected for publish comparison.
- Extend the modules publish workflow so outdated bundles are added to the existing auto publish PR set even when they were not part of the current diff.
- Define the comparison source explicitly so publish decisions are based on the registry state that matters for exposure, not just the current branch checkout.

## Capabilities

### New Capabilities
- `registry-publish-consistency`: Detect bundle manifests ahead of registry state and republish them through the existing automated registry PR flow.

### Modified Capabilities

## Impact

- Affected code: `scripts/publish-module.py`, `.github/workflows/publish-modules.yml`, and new/updated workflow tests.
- Affected systems: automated registry PR creation, bundle version monotonicity checks, and branch-to-registry publish decision logic.
- Dependencies: workflow must read bundle manifests, registry metadata, and the target comparison branch consistently.
