## Why

SpecFact's existing code-review surface enforces clean-code via the principle categories `naming | kiss | yagni | dry | solid | clean_code | architecture` through semgrep, ruff, pylint, radon, and AST runners. Those categories catch *size* and *structure* problems (LOC thresholds, swallowed exceptions, banned generic names, nesting depth), but they do not target the **shape of AI-generated code bloat**.

AI-generated code exhibits a recognisable pattern surface that current detectors miss as a category:

- re-implementations of single stdlib calls as 20+ line hand-rolled loops (manual `re`, `Counter`, `min`/`max`, `dict(zip(...))`, comprehension-equivalent `for`/`append` loops);
- defensive `try: ... except E: raise` blocks that catch and re-raise unchanged;
- single-call passthrough wrappers and `lambda x: f(x)` aliases;
- speculative `Optional[T] = None` parameters with no `is None` branch in the body;
- redundant intermediate variables assigned once and used once on the next line;
- long, linear functions with low cyclomatic complexity but high line count (LOC/complexity ratio anomaly).

Reviewers see these one by one and may flag them under `kiss` or `yagni`, but the bloat *category* is not surfaced as such, and there is no slash-command path that walks the user through targeted rewrites. The result is that AI bloat accumulates in modules at a faster rate than reviewers can manually triage it.

## What Changes

- **NEW**: Introduce `ai_bloat` as a new principle category alongside `naming | kiss | yagni | dry | solid | clean_code | architecture`, surfaced through the existing `ReviewFinding` transport and `.specfact/code-review.json` evidence file. Findings are emitted at `severity=info` (the existing non-blocking severity on `ReviewFinding`); the "advisory" framing is carried by the policy pack (`default_mode: advisory`) so they never block commits without requiring a new severity value.
- **NEW**: Add a packaged semgrep rule pack at `packages/specfact-code-review/resources/semgrep-rules/ai-bloat.yaml` covering pattern-shape detectors (manual-loop comprehension, passthrough lambda, identity try/except, none-then-none, single-call wrapper). Register the new rule IDs in `SEMGREP_RULE_CATEGORY` in `tools/semgrep_runner.py`.
- **NEW**: Add an AST-based runner at `packages/specfact-code-review/src/specfact_code_review/tools/ai_bloat_runner.py` covering semantic detectors that do not lend themselves to semgrep (unused Optional params, dead branches, LOC-vs-complexity anomalies, redundant intermediates), wired into the existing runner orchestration.
- **NEW**: Add a dedicated policy pack at `packages/specfact-code-review/resources/policy-packs/specfact/ai-bloat-patterns.yaml` registering the rules under `principle: ai_bloat`, parallel to `clean-code-principles.yaml` so the pack can be enabled or disabled independently.
- **NEW**: Add an IDE slash-command prompt at `packages/specfact-project/resources/prompts/specfact.08-simplify.md` that reads `.specfact/code-review.json`, filters findings where `category=ai_bloat`, and walks the user through each candidate with a per-change confirmation rewrite loop driven by the LLM in the IDE.
- **EXTEND**: Update the code-review module manifest version per semver patch rules and declare the new policy-pack and semgrep-rule resources in the bundle payload.

## Capabilities

### New Capabilities

- `code-review-ai-bloat-detection`: A new principle category, `ai_bloat`, exposed through the code-review runner pipeline. Includes a semgrep rule pack, an AST runner, a dedicated policy pack, and an IDE slash-command prompt that drives targeted rewrites.

### Modified Capabilities

- `clean-code-policy-pack`: Document the new `ai-bloat-patterns.yaml` policy pack as a parallel pack to `clean-code-principles.yaml`, including its enable/disable semantics and `advisory`-only severity model.

## Impact

- **Affected code**: `packages/specfact-code-review/` (new runner, new semgrep rules, new policy pack, manifest version bump, runner orchestration wiring); `packages/specfact-project/` (new packaged prompt resource and manifest payload).
- **Affected tests**: targeted unit tests per detector (one fixture pair per heuristic), semgrep rule fixture tests, policy-pack reference contract tests, and an integration test that exercises the end-to-end review pipeline against seeded bloat fixtures.
- **Affected docs**: reference docs for the `ai_bloat` category, the slash command, and the `advisory`-only model under code-review and review-run on modules.specfact.io, cross-referenced from `clean-code-principles` docs; root `README.md` headline callout; a quickstart walkthrough page demonstrating the end-to-end review → simplify → re-review flow with before/after evidence captured from a real repo; a modules.specfact.io homepage callout. All marketing copy uses the framing "bloat detection tuned for the shapes AI code commonly produces" and does not claim AI-authorship classification. A parallel callout in the core `specfact-cli` README is tracked as a follow-up issue out of scope for this PR.
- **Release impact**: patch version bumps and signature/registry updates for `specfact-code-review` (new resources) and `specfact-project` (new prompt resource); no breaking change to existing finding consumers because `ai_bloat` findings from both packages are purely additive and info-only (emitted at `severity=info`, never `warning` or `error`).

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Modules Epic**: [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162)
- **Parent Feature**: [#175](https://github.com/nold-ai/specfact-cli-modules/issues/175)
- **GitHub Issue**: [#269](https://github.com/nold-ai/specfact-cli-modules/issues/269)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/269>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
