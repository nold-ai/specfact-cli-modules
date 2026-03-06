## 1. OpenSpec And Test Setup

- [x] 1.1 Add or extend workflow-facing tests for bundle selection so a bundle ahead of the registry baseline fails when it is omitted from the publish set.
- [x] 1.2 Add or extend tests for the publish pre-check script so version comparison can use an explicit registry baseline rather than only the current checkout index.
- [x] 1.3 Capture the pre-implementation failing test commands and summaries in `openspec/changes/registry-republish-outdated-bundles/TDD_EVIDENCE.md`.

## 2. Workflow Implementation

- [x] 2.1 Extend the publish workflow bundle-resolution logic to union changed bundles with bundles whose manifests are newer than the selected registry baseline.
- [x] 2.2 Extend `scripts/publish-module.py` or a shared helper so version comparison can read the intended registry baseline explicitly.
- [x] 2.3 Update workflow logging and PR context to report why each bundle was selected for publish.

## 3. Validation

- [x] 3.1 Re-run the new workflow/script tests and capture the passing results in `openspec/changes/registry-republish-outdated-bundles/TDD_EVIDENCE.md`.
- [x] 3.2 Run `openspec validate registry-republish-outdated-bundles --strict`.
