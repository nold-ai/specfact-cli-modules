## Context

`specfact-cli-modules` now carries its own GitHub planning hierarchy, but parent Feature/Epic resolution is still manual and repeated. The goal is to make hierarchy lookup local and deterministic in the modules repo the same way it will be in core: a generated markdown inventory under ignored `.specfact/backlog/` becomes the first lookup surface, and the sync script only performs a full refresh when the Epic/Feature hierarchy changed.

This is a governance/runtime support change rather than a bundle feature. The output should stay self-contained in this repo and should not depend on the core repo’s cache file.

## Goals / Non-Goals

**Goals:**
- Generate a deterministic markdown cache of Epic and Feature issues for this repository.
- Include enough metadata for issue-parenting work without another GitHub lookup: issue number, title, short summary, labels, parent/child relationships, and issue URLs.
- Make the sync fast on no-op runs by using a small fingerprint/state check before regenerating markdown.
- Update repo guidance so contributors use the cache first and rerun sync only when needed.

**Non-Goals:**
- Replacing GitHub as the source of truth for modules-side hierarchy.
- Caching all issue types or full issue bodies.
- Sharing one cache file across both repos.
- Adding runtime coupling from bundle packages to GitHub sync logic.

## Decisions

### Reuse the same script contract as core, but keep files repo-local and ephemeral
The modules repo will implement the same cache contract as the core repo: sync script, state file, and deterministic markdown output. The generated files live under `.specfact/backlog/` so they remain local, ignored, and easy to regenerate.

Alternative considered:
- Import the core script from `specfact-cli`: rejected because governance tooling should work from this repo without special cross-repo bootstrapping.

### Use `gh api graphql` for hierarchy metadata
The script will use `gh api graphql` to retrieve issue type, labels, relationships, and summary fields in a compact way. This keeps the implementation aligned with the core repo and avoids bespoke HTML or REST stitching.

Alternative considered:
- `gh issue view/list` fan-out calls: too many calls and weaker relationship support.

### Split fingerprint detection from markdown rendering
The script will compute a fingerprint from Epic/Feature identity plus relevant change signals, compare it with a local state file, and skip markdown regeneration when nothing changed. When the fingerprint differs, it will fetch full data and rewrite the cache deterministically.

Alternative considered:
- Always rewrite the cache: simpler, but slower and noisier for routine use.

## Risks / Trade-offs

- [Core/modules drift] → Keep file names, output structure, and tests closely aligned across both repos.
- [GitHub metadata gaps] → Normalize missing parents, children, and summaries instead of failing on absent optional fields.
- [Users forget to refresh] → Make rerun conditions explicit in `AGENTS.md` and keep the no-op path cheap.

## Migration Plan

1. Add the sync script, state handling, markdown renderer, and tests in this repo.
2. Generate the initial modules-side cache file under ignored `.specfact/backlog/`.
3. Update `AGENTS.md` with cache-first GitHub parenting guidance.
4. Run verification and keep the paired core change aligned before implementation closes.

Rollback removes the script, cache, state file, and governance references without affecting bundle runtime code.

## Open Questions

- Whether a future follow-up should surface the cache in published docs, or keep it strictly as a maintainer artifact.
