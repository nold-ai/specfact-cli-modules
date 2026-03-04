---
name: Change Proposal
about: Propose a scoped modules-repo change (bundles, manifests, signing, CI, docs)
title: "[Change] <Brief Description>"
labels: enhancement, change-proposal
assignees: ''

---

## Why

Rationale and value for this change.

## What Changes

High-level implementation summary. Include affected bundles and workflow/config changes.

## Acceptance Criteria

- [ ] Bundle changes are scoped and intentional (`packages/*`)
- [ ] `module-package.yaml` versions are bumped where contents changed
- [ ] Manifests are re-signed
- [ ] `hatch run verify-modules-signature --require-signature --enforce-version-bump` passes
- [ ] Import boundaries respected (`hatch run check-bundle-imports`)
- [ ] Required quality gates pass in PR orchestrator

## Dependencies

List dependencies or blocked-by items.

## Related Issues/PRs

- Related to:
- Blocks:

## Additional Context

Add rollout notes, migration constraints, or branch protection implications.

---
OpenSpec Change Proposal: `change-id-here` (optional)
