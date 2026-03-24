## 1. Change Setup

- [ ] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-12-docs-validation-ci` entry
- [ ] 1.2 Add `modules-docs-command-validation` capability spec

## 2. Command Validation Script

- [ ] 2.1 Write `scripts/check-docs-commands.py` to extract command registrations from `packages/*/src/**/commands.py`
- [ ] 2.2 Compare extracted commands against code blocks in `docs/bundles/` and `docs/reference/commands.md`

## 3. Cross-Site Link Validation

- [ ] 3.1 Add link validation for cross-site URLs pointing to docs.specfact.io

## 4. CI Integration

- [ ] 4.1 Add docs validation step to CI workflow

## 5. Verification

- [ ] 5.1 Run validation locally and verify it catches broken examples
- [ ] 5.2 Run CI workflow end-to-end
