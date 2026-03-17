# Change: Modules Docs Canonical Site And Publishing Contract

## Why

`specfact-cli-modules` already ships its own Jekyll docs site, but that site is still positioned as a secondary GitHub Pages project URL while `specfact-cli` continues to host much of the same bundle documentation on the canonical docs domain. The result is duplicated maintenance, inconsistent ownership language, and no stable public docs identity for official bundle content.

The modules repository needs a clear docs contract of its own: official bundle and module documentation should publish independently on a first-class docs domain and present itself as the canonical home for deep module workflow guidance.

## What Changes

- Define the modules docs site as the canonical published home for official bundle and module-specific documentation.
- Update landing copy, site configuration, and navigation expectations so the site is ready for publication on a stable public docs domain rather than only the GitHub Pages project-path URL.
- Establish cross-site navigation rules linking modules docs back to `docs.specfact.io` and the core docs section.
- Prepare the content model for coordinated migration of duplicate bundle pages out of `specfact-cli` without requiring a combined docs build.

## Capabilities

### New Capabilities

- `modules-docs-publishing`: a stable publication and navigation contract for the dedicated modules docs site

## Impact

- Affected docs: `docs/_config.yml`, `docs/index.md`, `docs/_layouts/default.html`, and bundle-focused navigation/landing content in the modules docs set.
- User-facing impact: readers can discover a stable modules docs destination, understand that it is the canonical home for official bundle docs, and navigate back to the canonical docs entry point and core docs.
- Integration points: `specfact-cli` docs ownership wording and shared navigation labels must align with this site; Cloudflare-managed public docs domains will consume the resulting publication contract.
- Risk area: if the public-domain cutover lags behind content updates, the site must avoid hardcoding claims that point to a nonexistent live domain before DNS and routing are ready.

