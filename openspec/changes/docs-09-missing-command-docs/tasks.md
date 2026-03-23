## 1. Change Setup

- [ ] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-09-missing-command-docs` entry
- [ ] 1.2 Add capability specs for spec, govern, code-review, and codebase command docs

## 2. Spec Bundle Docs

- [ ] 2.1 Write `bundles/spec/validate.md`: spec validate + backward-compat with examples
- [ ] 2.2 Write `bundles/spec/generate-tests.md`: spec generate-tests workflow
- [ ] 2.3 Write `bundles/spec/mock.md`: spec mock server guide

## 3. Govern Bundle Docs

- [ ] 3.1 Write `bundles/govern/enforce.md`: govern enforce stage + govern enforce sdd deep guide
- [ ] 3.2 Write `bundles/govern/patch.md`: govern patch apply guide

## 4. Code Review Bundle Docs

- [ ] 4.1 Write `bundles/code-review/run.md`: code review run with --scope, --fix, --interactive options
- [ ] 4.2 Write `bundles/code-review/ledger.md`: ledger update/status/reset
- [ ] 4.3 Write `bundles/code-review/rules.md`: rules show/init/update

## 5. Codebase Bundle Docs

- [ ] 5.1 Write `bundles/codebase/analyze.md`: code analyze contracts
- [ ] 5.2 Write `bundles/codebase/drift.md`: code drift detect
- [ ] 5.3 Write `bundles/codebase/repro.md`: code repro

## 6. Verification

- [ ] 6.1 Validate all command examples against `--help` output
- [ ] 6.2 Verify all internal links resolve
- [ ] 6.3 Run `bundle exec jekyll build` with zero warnings
