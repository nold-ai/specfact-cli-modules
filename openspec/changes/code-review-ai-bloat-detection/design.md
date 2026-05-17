# Design

## Context

The code-review surface in `packages/specfact-code-review` already runs a multi-tool pipeline (semgrep, ruff, pylint, radon, basedpyright, contract-runner, AST clean-code visitor) and emits `ReviewFinding` records tagged with a principle category drawn from `naming | kiss | yagni | dry | solid | clean_code | architecture`. Findings flow through `.specfact/code-review.json` and surface in pre-commit via `scripts/pre_commit_code_review.py`, which blocks on `severity=error` only.

What the existing categories do *not* do is name AI-generated bloat as a distinct failure mode. KISS catches line-count outliers; YAGNI catches unused private helpers; DRY catches duplicate function shapes. But the specific *shapes* of AI bloat — manual loops that should be comprehensions, identity try/except, single-call wrappers, dead `Optional` plumbing — slip past these gates because each instance is individually defensible under the existing principle vocabulary.

This change introduces a new principle category, `ai_bloat`, with its own rule pack and policy pack, and a slash-command rewrite prompt that filters findings by category. The capability spans the `specfact-code-review` runner pipeline and the `specfact-project` prompt resources, so an explicit design precedes implementation.

## Goals / Non-Goals

**Goals:**
- Add `ai_bloat` as a new principle category in the existing `ReviewFinding` transport, with no schema change beyond a new accepted value for the `category` and `principle` fields. Findings emit at `severity=info` (the existing non-blocking severity), so `ReviewFinding.severity` keeps its current `error | warning | info` domain.
- Detect pattern-shape AI bloat via a packaged semgrep rule pack so detectors are declarative and tunable.
- Detect semantic AI bloat (dead `Optional` plumbing, LOC/complexity anomalies, redundant intermediates) via a sibling AST runner that mirrors the conventions of `ast_clean_code_runner.py`.
- Drive rewrites via a slash-command prompt that walks the user through each finding with per-change confirmation in the IDE, matching the existing CLI-detects / LLM-rewrites split used by `specfact.03-review.md`.
- Keep `ai_bloat` strictly advisory (per-finding `severity=info`, policy-pack `default_mode: advisory`) so pre-commit surfaces findings but never blocks.

**Non-Goals:**
- No autonomous `--fix` mode. Rewrites are LLM-mediated with per-change human confirmation; the CLI never rewrites source files.
- No cross-file refactors. All detectors operate at function or block scope inside a single file.
- No new error-severity findings. The `ai_bloat` category is `advisory`-only by policy.
- No new top-level module package. The capability extends `specfact-code-review` and adds one prompt resource to `specfact-project`.
- No change to the core CLI in `specfact-cli`. After the modules bundle republishes, the CLI's existing review pre-commit picks up the new findings automatically.

## Decisions

### Decision 1: Introduce `ai_bloat` as a new principle category, not a sub-mode of `kiss`/`yagni`

The detectors target a distinct failure mode with its own rewrite playbook (collapse to stdlib, remove dead plumbing, inline trivial wrappers) that does not map cleanly onto `kiss` or `yagni`. Folding it into either would dilute existing reviewer mental models and lose the ability to filter the IDE prompt by category. Adding a new principle is the minimal-cost surface change.

**Why**: `principle` is already a free-text string on `ReviewFinding`; adding a value is purely additive. The IDE prompt needs a clean filter predicate, and a dedicated principle is the simplest one.

**Alternative considered**: Reuse `kiss` and `yagni` and disambiguate via rule IDs. Rejected because it forces the slash-command prompt to maintain its own allow-list of rule IDs, and because reviewers reading the JSON cannot tell at a glance which `kiss` findings are AI-bloat vs. genuine LOC outliers.

### Decision 2: Split detectors between semgrep (pattern-shape) and AST runner (semantic)

Five detectors are pure syntactic patterns (manual-loop comprehension, passthrough lambda, identity try/except, none-then-none, single-call wrapper) and fit semgrep's declarative model. Four detectors require semantic reasoning (unused `Optional` param, dead branch, LOC/complexity ratio, redundant intermediate) and are easier to express as AST visitors with access to radon's already-collected complexity output.

**Why**: Each tool plays to its strengths. Semgrep rules are tunable without code changes and reuse the existing `semgrep_runner.py` orchestration, retry, and category mapping. AST visitors can correlate complexity, LOC, and usage signals across a function body in one pass.

**Alternative considered**: Put everything in semgrep. Rejected for the semantic detectors because semgrep cannot easily express "param `x` annotated `Optional[T] = None` but never tested for `None` inside the body". Pure-AST is also rejected because the pattern-shape detectors gain nothing from AST visitors and lose the declarative-config benefit.

### Decision 3: Ship a parallel policy pack, not entries appended to `clean-code-principles.yaml`

Policy packs are the existing unit of enable/disable in the code-review module. A parallel `ai-bloat-patterns.yaml` lets adopters opt in or out of bloat detection without touching the clean-code defaults, and keeps the lifecycle independent so future bloat-pattern revisions do not churn the clean-code pack.

**Why**: Independent lifecycle, independent telemetry, independent rollout. Cleaner separation for downstream consumers who may want clean-code defaults but not bloat detection (or vice versa).

**Alternative considered**: Append `ai_bloat` rules to `clean-code-principles.yaml`. Rejected because it couples two policy lifecycles and conflates two adopt/disable decisions into one.

### Decision 4: Slash-command prompt lives in `specfact-project`, not `specfact-code-review`

Prompt resources for the SpecFact workflow live in `specfact-project` (see `specfact.01-import.md`, `specfact.03-review.md`, etc.) so they are discovered as one bundle of slash commands. Putting the simplify prompt elsewhere would split discovery surface and inconsistent with prior placement.

**Why**: Consistency with the existing prompt-resource convention; downstream `.specfact/modules/specfact-project/resources/prompts/` listings include the new command without any new wiring.

### Decision 5: Advisory-only, never blocking (per-finding `severity=info`, policy-pack `default_mode: advisory`)

Bloat is judgment, not correctness. A 20-line manual loop is *suboptimal*, not *wrong*; a passthrough wrapper may be intentional API stability. Forcing the user to defend each finding at commit time would degrade signal-to-noise in the pre-commit gate and erode trust in the broader review surface.

**Why**: Match the lifecycle to the failure mode. The IDE slash command is the action surface; the pre-commit hook only surfaces awareness.

**Alternative considered**: High-confidence rules at `warning`, semantic rules at `advisory`. Deferred to a future iteration once detector precision in the field is known; this proposal keeps everything `advisory` to ship the first cut without false-positive risk.

## Detector Catalogue

### Semgrep rules — `resources/semgrep-rules/ai-bloat.yaml`

| Rule ID | Detects | Rewrite hint |
|---------|---------|--------------|
| `ai-bloat.manual-loop-comprehension` | `for x in xs: out.append(...)` shapes equivalent to a list/dict/set comprehension | Replace with comprehension or `map`/`filter` |
| `ai-bloat.passthrough-lambda` | `lambda x: f(x)` with no transformation | Use `f` directly |
| `ai-bloat.identity-try-except` | `try: ... except E: raise` with no transform, log, or context | Remove the try/except |
| `ai-bloat.none-then-none` | `if x is not None: return x; else: return None` | Return `x` directly |
| `ai-bloat.single-call-wrapper` | Function body is exactly `return other(args)` with no transform | Inline at callsite or alias the symbol |

### AST runner — `tools/ai_bloat_runner.py`

| Rule ID | Detects | Rewrite hint |
|---------|---------|--------------|
| `ai-bloat.unused-optional-param` | Parameter annotated `Optional[T] = None` with no `is None` branch in body | Make required or remove |
| `ai-bloat.dead-branch` | Branch unreachable given prior guards | Remove the branch |
| `ai-bloat.loc-vs-complexity` | Function LOC ≥ 40 with cyclomatic complexity ≤ 4 (long but linear) | Collapse to stdlib, comprehension, or smaller helper |
| `ai-bloat.redundant-intermediate` | Variable assigned once, read once on the immediately next line, with no naming clarity contribution | Inline the expression |

All findings emit with `category="ai_bloat"`, `principle="ai_bloat"`, `severity="info"` (non-blocking). The "advisory" framing is preserved at the policy-pack layer (`default_mode: advisory` in `ai-bloat-patterns.yaml`), not by adding a new severity value to `ReviewFinding`.

## Slash-Command Prompt

The new `specfact.08-simplify.md` mirrors the structure of `specfact.03-review.md`:

1. Reads `.specfact/code-review.json`.
2. Filters findings where `category == "ai_bloat"`.
3. Groups by file, then by rule ID.
4. For each finding: shows the bloated code block, names the rule, explains the rewrite hint, drafts the rewrite, and asks the user to accept / reject / skip / explain.
5. Applies accepted rewrites via the IDE's edit tool.
6. After the file is processed, suggests re-running `specfact code review run --json --out .specfact/code-review.json` to confirm the findings are gone.

The prompt never edits files autonomously and never skips the confirmation step.

## Risks

- **False positives on intentional API stability wrappers**: a single-call wrapper may exist deliberately to stabilise an API. Mitigation: `advisory` severity, slash-command confirmation step, and a future allow-list mechanism if field data warrants it.
- **Detector overlap with existing `kiss`/`yagni` rules**: some findings may surface under both. Mitigation: the slash-command filters strictly by `category=ai_bloat`, so duplication does not bleed into the simplify workflow; reviewers reading the raw JSON see both categorisations as intended.
- **Semgrep rule maintenance**: new rule patterns may need iteration on real code. Mitigation: package the rules as a versioned policy pack so updates are signature-tracked and ship with explicit version bumps.
