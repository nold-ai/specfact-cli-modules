---
name: specfact-code-review
description: CLI-grounded SpecFact code review workflow and house rules for AI coding sessions
allowed-tools: []
---

# House Rules - AI Coding Context / SpecFact Code Review Skill (v2)

Updated: 2026-05-22 | Module: nold-ai/specfact-code-review
## DO
- Use this skill when asked to run, interpret, or act on SpecFact code review in Codex CLI or another AI IDE
- Treat `specfact code review run --help` as authoritative; self-heal stale options by checking help before changing workflow
- For simplification queues, run `specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json`
- Ask for walkthrough level when interactive: vibe coder, junior developer, senior/pro, or headless agent; auto-adjust if obvious
- Interpret `guidance_kind`: `safe_mechanical` may apply after local safety checks, `needs_tests` requires tests first, `design_judgment` needs human choice, `preserve` means keep and log `preserve_reason`
- Log each simplification action as recommended, applied, kept, skipped, failed, with evidence of improvement or preserved contract
- In headless mode, process one file at a time and emit an action table: file, line, rule, guidance_kind, recommended_action, action_status, evidence
- For merge-quality review, run `specfact code review run --scope changed --bug-hunt --json --out .specfact/code-review.json`
- Ask whether tests should be included before repo-wide review; default to excluding tests unless test changes are the target
- Use intention-revealing names; avoid placeholder public names like data/process/handle
- Keep functions under 120 LOC, shallow nesting, and <= 5 parameters (KISS)
- Delete unused private helpers and speculative abstractions quickly (YAGNI)
- Extract repeated function shapes once the second copy appears (DRY)
- Split persistence and transport concerns instead of mixing `repository.*` with `http_client.*` (SOLID)
- Add @require/@ensure (icontract) + @beartype to all new public APIs
- Run hatch run contract-test-contracts before any commit
- Write the test file BEFORE the feature file (TDD-first)
## DON'T
- Don't copy prompt templates into AI IDEs when this installed skill can carry the reusable workflow guidance
- Don't treat simplification findings as AI-authorship proof or apply batch rewrites without explicit user approval
- Don't enable known noisy findings unless you explicitly want strict/full review output
- Don't use bare except: or except Exception: pass
- Don't add # noqa / # type: ignore without inline justification
- Don't mix read + write in the same method or call `repository.*` and `http_client.*` together
- Don't import at module level if it triggers network calls
- Don't hardcode secrets; use env vars via pydantic.BaseSettings
## TOP VIOLATIONS (auto-updated by specfact code review rules update)
<!-- auto-managed: do not edit manually -->
