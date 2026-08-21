---
name: specfact-code-review
description: Use for SpecFact code review workflows, especially when the user asks to remove AI bloat, simplify code, apply clean-code patterns, reduce boilerplate, fix review findings, or interpret SpecFact guidance.
allowed-tools: []
---

# SpecFact Code Review Skill

Updated: 2026-05-22 | Module: nold-ai/specfact-code-review

Use this skill as an interactive cleanup coach, not a raw lint executor. When a user says "remove AI bloat", "simplify", "apply clean code", "fix SpecFact review", or similar, run the SpecFact review workflow, explain decisions in the user's language, show exact patch previews, and validate after small changes.
Operating guidance: command examples in this skill are not the source of truth; CLI help is authoritative. Check `specfact code review run --help`, and ask the user before guessing when help output disagrees.

## DO

- Treat `specfact code review run --help` as authoritative; use `--instructions` as the fallback AI workflow when prompts/skills are unavailable
- For simplification queues, run `specfact code review run --scope changed --enforcement shadow --focus simplify --json --out .specfact/code-review-simplify.json`
- Ask for walkthrough level when interactive: vibe coder, junior developer, senior/pro, or headless agent; auto-adjust if obvious
- For vibe coders, present each finding as a decision card: plain-language issue, why it might need to stay, exact patch preview, validation plan, and recommended choice
- Interpret `guidance_kind`: `safe_mechanical` may apply after local safety checks, `needs_tests` requires tests first, `design_judgment` needs human choice with intent evidence, `preserve` means keep and log `preserve_reason`
- For `design_judgment`, inspect API, callback, framework hook, adapter, public symbol, CLI boundary, compatibility shim, and readability intent; if intent is unclear, default to keep or skip
- Log each simplification action as recommended, applied, kept, skipped, failed, with evidence of improvement or preserved contract
- In headless mode, process one file at a time and emit an action table: file, line, rule, guidance_kind, recommended_action, action_status, evidence
- Run targeted tests or rerun simplify review after each accepted file or very small batch; if validation cannot prove safety, downgrade to `needs_tests` or `skipped`
- For merge-quality review, run `specfact code review run --scope range --base-ref <full-base-ref> --head-ref <full-head-ref> --pr-context-file <event-derived-absolute-path> --enforcement full`; local output is `range_preview` until a protected consumer verifies and promotes it
- Ask whether tests should be included before repo-wide review; default to excluding tests unless test changes are the target
- Use intention-revealing names; avoid placeholder public names like data/process/handle
- Keep functions under 120 LOC, shallow nesting, and <= 5 parameters (KISS)
- Delete unused private helpers and speculative abstractions quickly (YAGNI)
- Extract repeated function shapes once the second copy appears (DRY)
- Split persistence and transport concerns instead of mixing `repository.*` with `http_client.*` (SOLID)
- Add @require/@ensure (icontract) + @beartype to all new public APIs
- Run hatch run contract-test-contracts before any commit
- Write the test file BEFORE the feature file (TDD-first)
- Return typed values from all public methods and guard chained attribute access

## DON'T

- Don't copy prompt templates into AI IDEs when this installed skill can carry the reusable workflow guidance
- Don't treat simplification findings as AI-authorship proof or apply batch rewrites without explicit user approval
- Don't ask non-expert users to infer code intent from a raw warning; provide the evidence and safest recommendation
- Don't apply `design_judgment` findings just because the patch looks shorter
- Don't enable known noisy findings unless you explicitly want strict/full review output
- Don't use bare except: or except Exception: pass
- Don't add # noqa / # type: ignore without inline justification
- Don't mix read + write in the same method or call `repository.*` and `http_client.*` together
- Don't import at module level if it triggers network calls
- Don't hardcode secrets; use env vars via pydantic.BaseSettings
- Don't create functions that exceed the KISS thresholds without a documented reason

## TOP VIOLATIONS (auto-updated by specfact code review rules update)
<!-- auto-managed: do not edit manually -->
