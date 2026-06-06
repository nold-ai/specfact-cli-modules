## Why

The first `ai_bloat` pass identifies common AI-shaped bloat, but its findings are still mostly local line-level hints. SpecFact needs a deterministic simplification feedback loop that can tell an IDE LLM what pattern to collapse, what related duplicate-intent code exists, and how much noise can likely be removed without turning advisory cleanup into a blocking gate.

## What Changes

- Add structured simplification metadata to code-review findings so `.specfact/code-review.json` can carry rewrite hints, confidence, estimated deletion impact, canonical patterns, intent keys, and related locations.
- Add deterministic simplification analyzers in `specfact-code-review` for expanded overengineering patterns: accumulator loops, verbose boolean returns, redundant `None` branches, wrapper chains, pass-through defensive `try/except`, one-use temporaries, table-lookup candidates, and stdlib replacement candidates.
- Add duplicate-intent grouping for functions in the same business/domain area using static AST shape, call roots, imports, path domain, and business vocabulary. This is not an LLM authorship classifier and does not use embeddings in v1.
- Add `--focus simplify` to review runs as a targeted queue for `ai_bloat`, high-confidence `dry`, and high-confidence `kiss` simplification findings.
- Update `/specfact.08-simplify` so IDE agents group findings by `intent_key -> file/domain -> rule`, show related locations, and still require explicit per-change confirmation before editing.
- Keep all new simplification findings advisory, score-neutral, and non-blocking.

## Capabilities

### New Capabilities

- `code-review-simplification-feedback`: Deterministic simplification metadata, duplicate-intent grouping, and IDE feedback queue behavior for code review findings.

### Modified Capabilities

- `review-finding-model`: Add optional simplification metadata fields while preserving backward compatibility for existing finding consumers.
- `review-run-command`: Add `--focus simplify` behavior for targeted simplification review queues.
- `clean-code-analysis`: Clarify how high-confidence `dry` and `kiss` signals can contribute to the simplification queue without changing their blocking policy.

## Impact

- **Affected bundles:** `packages/specfact-code-review` and `packages/specfact-project`.
- **Affected interfaces:** `.specfact/code-review.json` receives additive optional metadata and a schema-version bump to `1.1`; existing fields and consumers remain compatible.
- **Affected prompt resources:** `packages/specfact-project/resources/prompts/specfact.08-simplify.md`.
- **Affected docs:** code-review and prompt documentation on modules.specfact.io should describe the simplify focus, advisory-only model, and duplicate-intent grouping.
- **Release impact:** module package version bumps and signature refresh are required when implementation changes packaged resources or manifests.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Modules Epic:** [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162)
- **Parent Feature:** [#275](https://github.com/nold-ai/specfact-cli-modules/issues/275)
- **GitHub Issue:** [#276](https://github.com/nold-ai/specfact-cli-modules/issues/276)
- **Repository:** nold-ai/specfact-cli-modules
- **Prior Baseline:** [#269](https://github.com/nold-ai/specfact-cli-modules/issues/269) / `code-review-ai-bloat-detection`
- **Last Synced Status:** proposed
- **Sanitized:** false

## Follow-ups

- Add issues [#275](https://github.com/nold-ai/specfact-cli-modules/issues/275) and [#276](https://github.com/nold-ai/specfact-cli-modules/issues/276) to the `SpecFact CLI` project board. The current GitHub token created labels, issue type, and parent/subissue relationships successfully but returned `Resource not accessible by personal access token` for project assignment.
