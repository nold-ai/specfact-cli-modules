## Context

The current simplify flow emits useful candidates but does not always tell an LLM what to do safely. The most important missing distinction is between accidental structure and meaningful structure. Examples:

- `@require(lambda ...)` and `@ensure(lambda ...)` are contract expressions, not pass-through bloat.
- Optional parameters on abstract adapters may preserve protocol compatibility even if a concrete implementation does not use them.
- Small wrappers can be domain predicates, public compatibility boundaries, or CLI affordances.
- Long low-complexity functions may be readable orchestration rather than bloat.

The review output must encode these distinctions deterministically so an AI IDE or headless agent can act without guessing.

## Goals / Non-Goals

**Goals:**

- Add action-oriented guidance to simplify findings while keeping JSON backward-compatible.
- Make safe mechanical cleanup enforceable and optionally fixable.
- Keep judgment-heavy and preserve-worthy patterns out of automatic cleanup.
- Make `/specfact.08-simplify` interactive and adaptive to user experience level.
- Make the `specfact-code-review` skill give LLMs the same cleanup policy in IDE and CLI contexts.

**Non-Goals:**

- No LLM or embedding classifier inside the CLI.
- No automatic refactor for design-judgment findings.
- No breaking removal of existing simplification metadata fields.
- No claim that findings prove AI authorship.

## Decisions

### Decision 1: Extend finding guidance instead of adding a second artifact

The JSON report remains the source of truth. Each simplification finding can carry:

- `guidance_kind`: `safe_mechanical`, `needs_tests`, `design_judgment`, or `preserve`;
- `recommended_action`: `remove`, `inline`, `collapse`, `deduplicate`, `make_required`, `keep`, or `inspect`;
- `clean_code_principle`: `kiss`, `dry`, `yagni`, `contracts`, `api_stability`, or `readability`;
- `rationale`, `safety_checks`, `preserve_reason`, and `action_status`;
- optional before/after evidence and improvement metrics after an auto-applied safe fix.

Existing fields such as `confidence`, `rewrite_hint`, `canonical_pattern`, `intent_key`, and `related_locations` remain valid.

### Decision 2: Classify before enforcing

`--focus simplify` should emit all relevant guidance kinds, but only `safe_mechanical` findings may become enforceable. `needs_tests`, `design_judgment`, and `preserve` remain non-blocking and non-autofix.

### Decision 3: Preserve meaningful patterns explicitly

False-positive-prone contexts are not merely suppressed; they should produce `preserve` findings when that helps the user understand why cleanup is not recommended. Contract lambdas, abstract/protocol adapter params, public compatibility wrappers, CLI boundary wrappers, and domain-named predicates should include a `preserve_reason`.

### Decision 4: Prompt and skill are part of the product

The slash prompt and skill are the interactive delivery surface for the target audience. They must ask for or infer walkthrough level and adjust wording:

- vibe coder: teaching flow, one finding at a time;
- junior developer: principle, risk, test, proposed edit;
- senior/pro: concise grouped triage;
- headless agent: deterministic JSON-first behavior with no broad refactors.

### Decision 5: Evidence must show outcome, not just recommendation

When `--fix` applies a safe rewrite, the report should record what was recommended, what changed, what remains, and the improvement. For manual prompt flows, the prompt should summarize accepted, skipped, kept, and still-present findings after rerunning review.

## Risks / Trade-offs

- **Over-enforcement:** Limit blocking to `safe_mechanical` only.
- **Autofix risk:** Restrict `--fix` to small AST-safe rewrites with post-review evidence.
- **Prompt overwhelm:** Start with walkthrough level and group by guidance kind and intent.
- **Schema churn:** Keep all fields optional and validate legacy reports.
- **False-positive confusion:** Prefer explicit `preserve` with reason over silent disappearance where a finding would otherwise be tempting to fix.
