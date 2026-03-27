# Change: Add CI Validation For Docs Command Examples And Cross-Site Links (Modules Side)

## Why

Documentation command examples can drift from actual module implementations. Cross-site links to docs.specfact.io can break when core pages are moved. Older published pages can also keep missing front matter or broken internal links after the IA restructure unless they are explicitly cleaned up. This is the modules-side counterpart to the core-side docs-12 change.

## What Changes

- Add a script that extracts command registrations from all `packages/*/src/**/commands.py` and compares against command examples across published module docs under `docs/`
- Add cross-site link validation for links from modules docs to core docs
- Add checks that docs do not point users at legacy core-owned prompt/template paths when those resources are bundle-owned
- Clean up remaining stale published-doc warnings so the docs review run is warning-free
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
