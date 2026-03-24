# Design: clean-code-02-expanded-review-module

## Summary

This change expands the `specfact-code-review` bundle in place rather than creating a second review product. The new functionality falls into four slices:

1. finding schema expansion and category ownership
2. runner expansion for KISS, SOLID, YAGNI, DRY, and PR checklist analysis
3. policy-pack payload shipping for downstream policy consumers
4. canonical house-rules skill refresh

## Decisions

### Schema ownership

- Extend the existing `ReviewFinding` / `ReviewReport` category set with `naming`, `kiss`, `yagni`, `dry`, and `solid`.
- Keep severity handling generic; policy mode determines whether a finding blocks.

### Runner design

- Use semgrep for the lightweight naming and exception-pattern rules.
- Extend `radon_runner.py` with AST-derived LOC, nesting, and parameter metrics.
- Implement dedicated AST tools for solid, yagni, and dry checks so the bundle stays Python-native.
- Keep the PR checklist runner advisory-only and attach it through PR mode rather than normal file-only review runs.

### Policy-pack payload

- Ship the clean-code pack with the bundle so `policy-02-packs-and-modes` can consume it without redefining rule IDs.
- Per-rule mode resolution stays in specfact-cli policy code; this repo only owns the pack manifest and rule inventory.

### Dry-clone detector spike

- The AST clone detector is the riskiest part of the plan.
- The spec keeps the algorithm bounded to normalized-AST hashing and overlap thresholds rather than promising cross-language or whole-repo semantic clone detection.
