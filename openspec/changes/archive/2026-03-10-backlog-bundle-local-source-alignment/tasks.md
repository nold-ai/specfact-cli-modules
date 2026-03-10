## 1. Spec And Test Setup

- [x] 1.1 Add regression coverage for pytest bootstrap source alignment so user-home bundle paths cannot shadow local backlog bundle imports during gate runs.
- [x] 1.2 Capture the pre-implementation failing gate command and summary in `openspec/changes/backlog-bundle-local-source-alignment/TDD_EVIDENCE.md`.

## 2. Test Bootstrap Fix

- [x] 2.1 Harden `tests/conftest.py` to remove user-home bundle source paths and purge shadowed bundle modules before local imports.
- [x] 2.2 Reassert local bundle source alignment at pytest session start and before each test.

## 3. Validation

- [x] 3.1 Re-run the new regression test and the previously failing backlog tests, then capture the passing results in `openspec/changes/backlog-bundle-local-source-alignment/TDD_EVIDENCE.md`.
- [x] 3.2 Re-run `hatch run contract-test`.
- [x] 3.3 Re-run `hatch run smart-test`.
- [x] 3.4 Run `openspec validate backlog-bundle-local-source-alignment --strict`.
