## Context

The current simplify report already has per-finding `estimated_deletion_lines`, `guidance_kind`, `recommended_action`, `safety_checks`, and action status. That is enough for an expert to inspect individual findings, but it is not enough for a user or AI IDE to decide where to start, estimate cleanup impact, or distinguish a safe patch preview from a judgment call.

The next layer should stay deterministic and Python-first. CPG, Joern, and polyglot clone analysis remain follow-up work. This change should improve the current runner without adding a heavy default dependency path or turning bloat advisories into proof of AI authorship.

## Decisions

- `cleanup_forecast` is derived from reviewed Python LOC and guided simplification metadata. It reports raw finding counts and normalized metrics so teams can compare repositories and PRs without over-weighting file size.
- Forecast weights are fixed in V1: `safe_mechanical=1.0`, `needs_tests=0.6`, `design_judgment=0.25`, and `preserve=0.0`.
- `--preview-fixes` is non-mutating. It may create temporary files or in-memory diffs, but it must not edit tracked sources.
- `--with-mutation` is explicit and valid only with `--focus simplify`. Timeouts and tool absence are inconclusive evidence, not proof that cleanup is safe.
- Preserve reasons short-circuit automatic cleanup. The closed taxonomy covers contract, public API, protocol/ABC, CLI callback, compatibility shim, explicit marker, spec/domain wrapper, and load-bearing mutation evidence.
- `remediation_packet` is the universal handoff surface. IDE prompts and skills may summarize it, but the JSON is authoritative.

## Data Shape

`cleanup_forecast` should include:

- `reviewed_loc`: production, test, and total Python LOC for the reviewed file set.
- `estimated_deletion_lines`: low, expected, high, plus totals by guidance kind.
- `ai_bloat_index`: findings per KLOC, weighted bloat points per KLOC, and cleanup-yield LOC per KLOC.
- `by_guidance_kind`: counts and estimated deletion lines for each guidance kind.
- `by_action_status`: lifecycle counts when present.

Finding additions should be optional:

- `signal_trace`: deterministic source signals, including tool name, fired flag, score/value, evidence reference, and explanation.
- `preserve_reasons`: closed-list preserve reasons with evidence refs.
- `remediation_packet`: plain-language issue, recommended action, why it may need to stay, safety checks, validation plan, safe-to-autofix flag, and optional patch forecast refs.

## Risks

- **Forecasts can look like guarantees.** Mitigation: use low/expected/high ranges and label deletion estimates as non-binding until preview or mutation evidence exists.
- **Mutation can be slow or flaky.** Mitigation: keep it opt-in, candidate-scoped, and inconclusive on timeout.
- **Preserve detection can hide real bloat.** Mitigation: preserve only blocks automatic cleanup; it can still be reported as kept with rationale.
- **JSON growth can break consumers.** Mitigation: additive fields only, keep original required fields and legacy validation intact.
