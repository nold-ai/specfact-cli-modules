## Context

`code-review-ai-bloat-detection` added the first advisory `ai_bloat` layer: semgrep rules for syntactic shapes, an AST runner for local semantic patterns, a policy pack, and `/specfact.08-simplify`. The current output is useful but still shallow for an IDE loop because most findings carry only category, rule, file, line, and message.

The next step is to make the CLI output richer while keeping the responsibility split clear:

- the CLI deterministically detects and groups simplification opportunities;
- the IDE LLM proposes rewrites from that evidence;
- the user approves each edit.

This change is owned by `specfact-cli-modules`, primarily `packages/specfact-code-review` and `packages/specfact-project`. No core CLI schema dependency is required for v1 because the JSON extension is additive.

## Goals / Non-Goals

**Goals:**

- Add optional simplification metadata to `ReviewFinding` without breaking existing JSON consumers.
- Add deterministic static signals for common overengineering patterns that are safe to present as cleanup candidates.
- Group duplicate-intent code in the same business/domain area so users see consolidation opportunities instead of unrelated one-line warnings.
- Add `--focus simplify` as a review command convenience for feeding `/specfact.08-simplify`.
- Update the simplify prompt to use grouped evidence while preserving per-change confirmation.

**Non-Goals:**

- No LLM, embeddings, or authorship classification inside the CLI.
- No autonomous `--fix` behavior for simplification findings.
- No blocking or score penalty for simplification findings in v1.
- No cross-language implementation in v1; Python remains the supported analysis target.
- No breaking removal or rename of existing `ReviewFinding` fields.

## Decisions

### Decision 1: Add optional metadata on findings instead of a second report artifact

Simplification metadata belongs beside each finding because the IDE prompt already reads `.specfact/code-review.json` and filters findings by category/rule. A second file would create synchronization and stale-data risk.

The metadata fields are optional:

- `confidence`: deterministic confidence bucket or score for prioritization;
- `rewrite_hint`: concise standard-pattern guidance;
- `canonical_pattern`: normalized pattern label such as `manual-accumulator-loop` or `verbose-bool-return`;
- `intent_key`: stable grouping key for related domain intent;
- `estimated_deletion_lines`: non-binding estimate used for triage;
- `related_locations`: same-shape or same-intent locations that should be reviewed together.

Existing consumers can ignore unknown fields.

### Decision 2: Use static-first duplicate-intent grouping

The duplicate-intent detector should compute a grouping key from deterministic ingredients:

- normalized AST shape with local names/literals erased;
- call roots and imported APIs;
- function name tokens after stop-word removal;
- path/domain tokens from package and module path;
- docstring/comment vocabulary only as weak evidence.

This catches “same business operation written twice with different names” without requiring external services or an LLM. The detector should emit only when multiple signals agree; ambiguous groups stay silent.

### Decision 3: Keep policy advisory and score-neutral

Overengineering signals often require human context: wrappers may preserve API compatibility, verbose branches may aid debugging, and duplicate-looking code may intentionally diverge. Therefore every new signal stays advisory and score-neutral in v1. The action surface is the IDE prompt, not pre-commit blocking.

### Decision 4: Reuse `--focus` rather than adding a separate command

`review-run-command` already supports repeatable `--focus` facets. Extending that option with `simplify` avoids a new top-level command while giving users and prompts a stable way to request the simplification queue. `--focus simplify` filters findings after normal analysis to the set intended for simplification review.

### Decision 5: Prompt groups before edits

`/specfact.08-simplify` should first group by `intent_key`, then by file/domain and rule. This lets the IDE explain consolidation opportunities before suggesting a rewrite, but it must continue to apply only one accepted edit at a time.

## Risks / Trade-offs

- **False positives on intentional wrappers** -> Use high-confidence thresholds, advisory severity, and explicit accept/reject/skip confirmation.
- **Metadata churn in JSON consumers** -> Keep fields optional and bump schema version additively to `1.1`.
- **Duplicate-intent grouping overreach** -> Require agreement across AST shape plus domain/call evidence; never group solely by similar names.
- **Prompt overwhelms users on large repos** -> Use `--focus simplify` and grouped ranking by confidence and estimated deletion.
- **Project board assignment gap** -> GitHub token could not add issues to the project; record as a setup follow-up before implementation readiness.
