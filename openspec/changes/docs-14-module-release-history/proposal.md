# Change: Publish-Driven Module Release History And Docs Rendering

## Why

The modules docs homepage currently tells users what each official module does, but it does not answer the more operational question: which module versions have been published recently, and what features or improvements each release shipped. The repository-level `CHANGELOG.md` is not a good source for that view because it is prose-first, repo-level, and not consistently structured per module/version. The publish workflow already updates `registry/index.json` whenever a module is released, so release-history metadata should be captured in the same publish path and then rendered in docs from repository data without dynamic loading.

Already-published module versions also need historical coverage so the feature is useful from day one. That requires a one-time backfill from existing repo evidence with AI-assisted extraction, followed by a stable structured format for future publishes. OpenSpec project rules should also be tightened so release-history extraction/update becomes part of the expected workflow for future module releases and docs refreshes.

## What Changes

- Define a canonical structured release-history source for official modules, separate from the lean install/search registry index
- Extend `.github/workflows/publish-modules.yml` so each published module version writes a release-history entry alongside the existing registry metadata update
- Add a one-time backfill workflow for already-published module versions using AI-assisted extraction from existing repo evidence and human-reviewable structured output
- Let AI copilot draft module-specific release and patch notes in a regular changelog style, but constrained to clear user-facing scope, shipped value, and concise summaries rather than low-signal technical detail
- Render recent per-module release history in the modules docs overview so users can immediately see published versions and shipped features/improvements
- Document the authoring/publish expectations for maintaining release-history metadata
- Update `openspec/config.yaml` rules so future changes involving module releases or docs synchronization account for release-history extraction/update requirements

## Capabilities

### New Capabilities

- `module-release-history-registry`: canonical structured release-history metadata for official module publishes
- `module-release-history-docs`: docs overview renders recent published module versions with shipped features and improvements
- `module-release-note-summarization`: AI-assisted release-note drafting produces user-facing module release summaries with explicit shipped scope and minimal technical noise

### Modified Capabilities

- `publish-modules-workflow`: publish automation writes release-history entries in addition to updating `registry/index.json`
- `openspec-project-rules`: OpenSpec configuration guides future release-oriented changes to include release-history extraction/update where applicable

## Impact

- New publish-driven data source under `registry/` and/or `docs/_data/`
- Modified workflow: `.github/workflows/publish-modules.yml`
- Modified docs: homepage/overview rendering plus publishing guidance
- Modified OpenSpec project config: `openspec/config.yaml`
- Backfill scope: existing published official module versions in `registry/index.json`

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #124
- **Issue URL**: https://github.com/nold-ai/specfact-cli-modules/issues/124
- **Last Synced Status**: synced
- **Sanitized**: true
