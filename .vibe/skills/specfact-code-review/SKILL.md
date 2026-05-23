---
name: specfact-code-review
description: House rules for AI coding sessions derived from review findings
allowed-tools: []
---

# House Rules - AI Coding Context (v4)

Updated: 2026-05-22 | Module: nold-ai/specfact-code-review

## DO

- For simplification queues, run `specfact code review run --scope changed --focus simplify --json --out .specfact/code-review-simplify.json`
- Ask for walkthrough level when interactive: vibe coder, junior developer, senior/pro, or headless agent; auto-adjust if obvious
- Interpret `guidance_kind`: `safe_mechanical` may apply after local safety checks, `needs_tests` requires tests first, `design_judgment` needs human choice, `preserve` means keep and log `preserve_reason`
- Log each simplification action as recommended, applied, kept, skipped, failed, with evidence of improvement or preserved contract
- In headless mode, process one file at a time and emit an action table: file, line, rule, guidance_kind, recommended_action, action_status, evidence
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

- Don't enable known noisy findings unless you explicitly want strict/full review output
- Don't use bare except: or except Exception: pass
- Don't add # noqa / # type: ignore without inline justification
- Don't mix read + write in the same method or call `repository.*` and `http_client.*` together
- Don't import at module level if it triggers network calls
- Don't hardcode secrets; use env vars via pydantic.BaseSettings
- Don't create functions that exceed the KISS thresholds without a documented reason

## TOP VIOLATIONS (auto-updated by specfact code review rules update)
<!-- auto-managed: do not edit manually -->
