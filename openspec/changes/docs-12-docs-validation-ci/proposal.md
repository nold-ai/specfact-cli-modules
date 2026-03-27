# Change: Add CI Validation For Docs Command Examples And Cross-Site Links (Modules Side)

## Why

Documentation command examples can drift from actual module implementations. Cross-site links to docs.specfact.io can break when core pages are moved. This is the modules-side counterpart to the core-side docs-12 change.

## What Changes

- Add a script that extracts command registrations from all `packages/*/src/**/commands.py` and compares against command examples across published module docs under `docs/`
- Add cross-site link validation for links from modules docs to core docs
- Add checks that docs do not point users at legacy core-owned prompt/template paths when those resources are bundle-owned
- Integrate into CI workflow

## Capabilities

### New Capabilities

- `modules-docs-command-validation`: CI check that module docs command examples match actual bundle implementations

## Impact

- New scripts: `scripts/check-docs-commands.py`
- Modified CI: docs validation step added
- Cross-repo: corresponds to specfact-cli/docs-12-docs-validation-ci

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #100
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/100
- **Last Synced Status**: synced
- **Sanitized**: true
- **Cross-repo**: specfact-cli/docs-12-docs-validation-ci
