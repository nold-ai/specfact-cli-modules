# Change Validation Report: docs-01-modules-docs-canonical-site

**Validation Date**: 2026-03-17
**Change Proposal**: [proposal.md](./proposal.md)
**Validation Method**: Dry-run documentation dependency and publication-contract analysis

## Executive Summary

- Breaking Changes: 0 detected at runtime
- Dependent Files: `README.md`, `docs/_config.yml`, `docs/index.md`, `docs/_layouts/default.html`, and bundle-focused navigation pages
- Impact Level: Medium (public docs identity and cross-site navigation change)
- Validation Result: Pass
- User Decision: Proceed with dedicated modules docs publication contract

## Breaking Changes Detected

None at runtime. This is documentation-site and publication-contract work only.

The main risk is public-link churn if the site starts claiming a first-class public domain before DNS/routing is available. That is mitigated by keeping wording domain-ready rather than claiming the cutover is already live until Cloudflare configuration exists.

## Dependencies Affected

### Critical Alignment Dependencies

- `README.md` still treats the GitHub Pages project URL as the docs target.
- `docs/_config.yml` still targets `https://nold-ai.github.io` with `baseurl: "/specfact-cli-modules"`.
- `docs/index.md` already claims canonical ownership for official module docs, but the surrounding site identity and navigation do not yet match that claim.
- `docs/_layouts/default.html` still uses the same top navigation structure as the core docs set and will need explicit cross-site labels (`Docs Home`, `Core CLI`, `Modules`).

### Cross-Repository Dependencies

- `specfact-cli` must update its docs portal and ownership language so module-specific deep pages in core become handoff/overview content rather than competing canonicals.
- Cloudflare/public-domain setup is required for final publication on `modules.docs.specfact.io`, but content and navigation alignment can land before that cutover.

## Impact Assessment

- **Code Impact**: None expected
- **Docs Impact**: Medium-to-high; site config, landing copy, and shared navigation are all in scope
- **Test Impact**: Lightweight docs assertions are appropriate for site identity, top-nav labels, and canonical ownership wording
- **Release Impact**: Low-to-medium; the main risk is publishing mixed signals about canonical URLs during the transition window

## Format Validation

- **proposal.md Format**: Pass
- **tasks.md Format**: Pass
- **specs Format**: Pass
- **Config.yaml Compliance**: Pass

## OpenSpec Validation

- **Status**: Pass
- **Command**: `openspec validate docs-01-modules-docs-canonical-site --strict`
- **Issues Found/Fixed**: 0
