## 1. Change Setup

- [x] 1.1 Update `openspec/CHANGE_ORDER.md` with `docs-09-missing-command-docs` entry
- [x] 1.2 Add capability specs for spec, govern, code-review, and codebase command docs

## 2. Spec Bundle Docs

- [x] 2.1 Write `bundles/spec/validate.md`: spec validate + backward-compat with examples
- [x] 2.2 Write `bundles/spec/generate-tests.md`: spec generate-tests workflow
- [x] 2.3 Write `bundles/spec/mock.md`: spec mock server guide

## 3. Govern Bundle Docs

- [x] 3.1 Write `bundles/govern/enforce.md`: govern enforce stage + govern enforce sdd deep guide
- [x] 3.2 Write `bundles/govern/patch.md`: govern patch apply guide

## 4. Code Review Bundle Docs

- [x] 4.1 Write `bundles/code-review/run.md`: code review run with --scope, --fix, --interactive options
- [x] 4.2 Write `bundles/code-review/ledger.md`: ledger update/status/reset
- [x] 4.3 Write `bundles/code-review/rules.md`: rules show/init/update

## 5. Codebase Bundle Docs

- [x] 5.1 Write `bundles/codebase/analyze.md`: code analyze contracts
- [x] 5.2 Write `bundles/codebase/drift.md`: code drift detect
- [x] 5.3 Write `bundles/codebase/repro.md`: code repro

## 6. Verification

- [x] 6.1 Validate all command examples against `--help` output
- [x] 6.2 Verify command docs that mention prompts/templates use bundle-owned resource language consistent with `packaging-01-bundle-resource-payloads`
- [x] 6.3 Verify all internal links resolve
- [x] 6.4 Run `bundle exec jekyll build` with zero warnings
