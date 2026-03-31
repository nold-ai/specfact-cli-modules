# Design: Module Release History As Publish-Driven Structured Data

## Summary

This change introduces a canonical structured release-history source for official modules and uses it to render user-facing release summaries in the modules docs. The source is updated by the publish workflow whenever a module version is released. Existing releases are backfilled once using AI-assisted extraction plus review. The repository-level `CHANGELOG.md` remains a narrative repo changelog and is not treated as the canonical machine-readable source.

## Design Goals

- Keep docs rendering static and repository-driven
- Avoid parsing prose from `CHANGELOG.md` at runtime or build time
- Ensure future publishes cannot forget release-history updates
- Support one-time historical backfill with human review
- Preserve a user-friendly summary of shipped features and improvements per module version
- Keep AI-generated release and patch notes clear, concise, and user-focused rather than implementation-noise-heavy

## Proposed Data Shape

Suggested canonical record fields:

- `module_id`
- `version`
- `published_at`
- `summary`
- `features`
- `improvements`
- `fixes`
- `breaking_changes`
- `source_refs`

Suggested authoring split:

- structured fields hold normalized release facts (`module_id`, `version`, `published_at`, categorized bullets)
- AI-generated summary fields turn those facts into concise user-facing release and patch notes for docs consumption

The canonical store should be append-only by module/version, with updates allowed only for corrective edits to already-recorded entries.

## Repository Placement

Preferred model:

- Canonical source under `registry/` because it is publish-owned metadata
- Optional docs projection under `docs/_data/` generated or synchronized from the canonical source for simple Jekyll rendering

This keeps install/search metadata lean in `registry/index.json` while preserving a richer history model elsewhere.

## Publish Integration

The publish workflow already detects changed bundles, builds artifacts, and updates `registry/index.json`. The same step should also persist a release-history entry for each published bundle version. That requires a stable input contract for release notes so publish automation is not forced to infer meaning from code diffs at publish time.

Possible input sources:

- manifest-adjacent structured release note file committed with the change
- release metadata block in `module-package.yaml`
- curated workflow input consumed by the publish action

The most maintainable path is a committed structured source in the repo so the release note content is reviewable in PRs and can later feed docs automatically.

## AI Release Note Style

AI-assisted release-note drafting should be constrained by explicit project rules:

- summarize shipped user-facing scope first
- prefer concrete feature/improvement bullets over internal implementation detail
- avoid jargon-heavy narration unless needed for user understanding
- avoid empty hype and generic filler phrasing
- keep patch notes concise and scannable
- make clear which module and version each note applies to

## Historical Backfill

Already-published versions in `registry/index.json` need initial coverage. Because there are no per-module tags and `CHANGELOG.md` is incomplete/module-skewed, backfill should use AI-assisted extraction from:

- module manifest version history available in repo history
- merged PR descriptions and commit messages where available
- root `CHANGELOG.md`
- docs additions that clearly announce new commands/features

Backfilled entries must be marked as reviewed before becoming canonical.

## OpenSpec Rule Updates

`openspec/config.yaml` should gain rules that make release-history updates explicit when a change:

- modifies a published module payload
- changes docs that summarize current module capabilities
- introduces or revises publish automation for official modules

This keeps future docs and publish metadata aligned without relying on memory.

It should also add release-note generation guidance so future AI-assisted updates use the same user-focused summarization style during publish and backfill work.
