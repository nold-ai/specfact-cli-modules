---
name: specfact-code-review
description: House rules for AI coding sessions derived from review findings
allowed-tools: []
---

# House Rules - AI Coding Context (v1)

Updated: 2026-03-30 | Module: nold-ai/specfact-code-review

## DO
- Ask whether tests should be included before repo-wide review; default to excluding tests unless test changes are the target
- Use intention-revealing names; avoid placeholder public names like data/process/handle
- Keep functions under 120 LOC, shallow nesting, and <= 5 parameters (KISS)
- Delete unused private helpers and speculative abstractions quickly (YAGNI)
- Extract repeated function shapes once the second copy appears (DRY)
- Split persistence and transport concerns instead of mixing repository.* with http_client.* (SOLID)
- Add @require/@ensure (icontract) + @beartype to all new public APIs
- Run hatch run contract-test-contracts before any commit
- Write the test file BEFORE the feature file (TDD-first)
- Return typed values from all public methods and guard chained attribute access

## DON'T
- Don't enable known noisy findings unless you explicitly want strict/full review output
- Don't use bare except: or except Exception: pass
- Don't add # noqa / # type: ignore without inline justification
- Don't mix read + write in the same method or call repository.* and http_client.* together
- Don't import at module level if it triggers network calls
- Don't hardcode secrets; use env vars via pydantic.BaseSettings
- Don't create functions that exceed the KISS thresholds without a documented reason

## TOP VIOLATIONS (auto-updated by specfact code review rules update)
<!-- auto-managed: do not edit manually -->
