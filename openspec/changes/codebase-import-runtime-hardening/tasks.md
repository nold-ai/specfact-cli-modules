# Tasks: codebase-import-runtime-hardening

## 1. GitHub readiness and change scaffolding

- [ ] 1.1 Verify `.specfact/backlog/github_hierarchy_cache.md` is fresh, confirm the new change fits the `specfact code` epic, and create or sync the parent Feature plus change issue with labels, project assignment, blockers, and concurrency checks recorded.
- [ ] 1.2 Add `codebase-import-runtime-hardening` to `openspec/CHANGE_ORDER.md` under the appropriate pending section with its parent Feature and GitHub issue links.
- [ ] 1.3 Validate the new change artifacts with `openspec validate codebase-import-runtime-hardening --strict` before implementation begins.

## 2. Spec-first failing tests

- [ ] 2.1 Add focused tests for import traversal defaults and warnings, including dot-prefixed directories, virtual environments, build outputs, `.specfact/.specfactignore`, and progress totals used for ETA reporting.
- [ ] 2.2 Add focused tests for packaged runtime generator templates so missing `.j2` resources fail before code changes.
- [ ] 2.3 Run the targeted tests to capture failing-before evidence and record the commands, timestamps, and failures in `openspec/changes/codebase-import-runtime-hardening/TDD_EVIDENCE.md`.

## 3. Import runtime hardening

- [ ] 3.1 Introduce a shared ignore-policy helper for code import traversal that prunes hidden and heavyweight directories before discovery while honoring repo-local `.specfact/.specfactignore`.
- [ ] 3.2 Apply that policy consistently across file counting, analyzer discovery, relationship extraction, and AI context loading, and surface warnings when unusually large artifact trees are skipped.
- [ ] 3.3 Replace fixed/optimistic ETA messaging with progress derived from discovered and processed work so reported remaining time tracks live import execution.

## 4. Runtime resource packaging and docs

- [ ] 4.1 Add the required project-bundle Jinja2 templates to packaged resources and resolve them from robust packaged/development paths in the affected generators.
- [ ] 4.2 Extend bundle payload tests and any manifest/resource metadata needed so shipped resources remain signed and versioned correctly.
- [ ] 4.3 Update user-facing docs for import defaults, ignore overrides, large-artifact warnings, and runtime template packaging expectations.

## 5. Passing evidence, quality gates, and review

- [ ] 5.1 Re-run the targeted import/runtime and resource tests, then record passing evidence in `openspec/changes/codebase-import-runtime-hardening/TDD_EVIDENCE.md`.
- [ ] 5.2 Run the required quality gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, `hatch run contract-test`, the relevant `hatch run smart-test`, and the relevant `hatch run test`.
- [ ] 5.3 Run `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope full`, fix every finding on modified artifacts, rerun until the report passes, and record the command and timestamp in `TDD_EVIDENCE.md`.
- [ ] 5.4 Commit, push, and open or update the PR to `dev` after verification is green.