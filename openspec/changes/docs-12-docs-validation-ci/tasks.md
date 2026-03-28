## 1. Change Setup

- [x] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-12-docs-validation-ci` entry
- [x] 1.2 Add `modules-docs-command-validation` capability spec

## 2. Command Validation Script

- [x] 2.1 Write `scripts/check-docs-commands.py` to extract command registrations from `packages/*/src/**/commands.py`
- [x] 2.2 Compare extracted commands against code blocks in `docs/bundles/` and `docs/reference/commands.md`
- [x] 2.3 Flag stale references to legacy core-owned prompt/template locations that were migrated by `packaging-01-bundle-resource-payloads`
- [x] 2.4 Expand command validation coverage to published module docs across `docs/`

## 3. Cross-Site Link Validation

- [x] 3.1 Add link validation for cross-site URLs pointing to docs.specfact.io

## 4. CI Integration

- [x] 4.1 Add docs validation step to CI workflow

## 5. Verification

- [x] 5.1 Run validation locally and verify it catches broken examples
- [x] 5.2 Run validation locally and verify it catches stale core-owned resource path references
- [x] 5.3 Run CI workflow end-to-end via the local docs-review-equivalent validator and test path documented in `TDD_EVIDENCE.md`
- [x] 5.4 Audit repo-wide published docs and remove stale former command references so validation passes with zero findings
- [x] 5.5 Remove the remaining docs-review warnings by adding missing front matter and fixing stale internal links in published docs
