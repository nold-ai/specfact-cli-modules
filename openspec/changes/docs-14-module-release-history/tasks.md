# 1. Change Setup

- [ ] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-14-module-release-history`
- [ ] 1.2 Add capability specs for structured module release history and docs rendering

## 2. Release History Data Model

- [ ] 2.1 Define a canonical structured schema for per-module release history with fields for module id, version, published date, shipped features, shipped improvements, and optional links/notes
- [ ] 2.2 Decide repository ownership for the canonical history source and any docs-consumable projection derived from it
- [ ] 2.3 Document why `CHANGELOG.md` remains a repo-level narrative changelog rather than the canonical module release-history source

## 3. Publish Workflow Integration

- [ ] 3.1 Extend `.github/workflows/publish-modules.yml` so each module publish writes a release-history entry together with the registry metadata update
- [ ] 3.2 Define the publish-time input contract for shipped features/improvements so the workflow can record user-friendly release notes without free-form drift
- [ ] 3.3 Define AI-assisted release-note drafting rules so copilot writes clear user-facing module release/patch notes with explicit shipped scope and no low-signal technical filler
- [ ] 3.4 Update publishing docs to describe the new release-history requirement, AI drafting rules, and review flow

## 4. Historical Backfill

- [ ] 4.1 Inventory already-published official module versions from `registry/index.json`
- [ ] 4.2 Define an AI-assisted backfill procedure that extracts candidate shipped features/improvements from existing repository evidence into the canonical structured format
- [ ] 4.3 Add human-review guidance so backfilled release-history entries are approved before becoming canonical
- [ ] 4.4 Ensure backfilled AI-generated summaries follow the same user-focused release-note style as future publish-time entries

## 5. Docs Rendering

- [ ] 5.1 Add homepage or overview rendering that clearly shows recent published module versions and their shipped features/improvements
- [ ] 5.2 Ensure docs rendering is build-time/static and does not depend on runtime network fetches
- [ ] 5.3 Provide graceful handling for modules with sparse or not-yet-backfilled history

## 6. OpenSpec Rule Updates

- [ ] 6.1 Update `openspec/config.yaml` rules so release-oriented changes include release-history extraction/update expectations where applicable
- [ ] 6.2 Add rule guidance for future docs updates that depend on publish-driven module history
- [ ] 6.3 Add rule guidance for AI copilot release-note generation style: user-facing benefits first, shipped scope explicit, and no unnecessary technical jargon or generic filler text

## 7. Verification

- [ ] 7.1 Verify the publish workflow can write a correct release-history entry for a newly published module version
- [ ] 7.2 Verify the docs overview renders release-history data accurately for all official modules
- [ ] 7.3 Verify the backfill procedure produces reviewable candidate entries for existing published versions
