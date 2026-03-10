# Implementation Tasks: bugfix-backlog-html-export-validation

## 1. Branch and worktree setup

- [x] 1.1 Create worktree from origin/dev: `git worktree add ../specfact-cli-worktrees/bugfix/backlog-html-export-validation -b bugfix/backlog-html-export-validation origin/dev`
- [x] 1.2 Change to worktree: `cd ../specfact-cli-worktrees/bugfix/backlog-html-export-validation`
- [x] 1.3 Bootstrap Hatch environment: `hatch env create`
- [x] 1.4 Verify pre-flight checks: `hatch run smart-test-status` and `hatch run contract-test-status`
- [x] 1.5 Applied spec delta from `openspec/changes/bugfix-backlog-html-export-validation/specs/backlog-daily-markdown-normalization/spec.md`

## 2. Implementation (Completed)

- [x] 2.1 Applied `_normalize_markdown_text` to comments in `_build_copilot_export_content` with defensive `str(c)` coercion
- [x] 2.2 Added input length guard (50KB) to `_normalize_markdown_text` for ReDoS mitigation
- [x] 2.3 Wrapped `_normalize_markdown_text` in try/except with fallback to strip tags on exception
- [x] 2.4 Added defensive `str(c)` coercion when iterating comments in both export and summarize loops
- [x] 2.5 Removed `@ensure` decorator from `_normalize_markdown_text` to prevent ViolationError from aborting export

## 3. Quality gates (All Passed)

- [x] 3.1 `hatch run format` - 274 files OK
- [x] 3.2 `hatch run type-check` - 0 errors, 0 warnings, 0 notes
- [x] 3.3 `hatch run lint` - 10.00/10 rating
- [x] 3.4 `hatch run contract-test` - 204 passed, 16 skipped
- [x] 3.5 `hatch run smart-test` - 204 passed, 16 skipped

## 4. Documentation and validation

- [ ] 4.1 Update docs if `--copilot-export` behavior is documented
- [x] 4.2 Run `openspec validate bugfix-backlog-html-export-validation --strict`

## 5. Version and PR (Pending)

- [ ] 5.1 Bump patch version in specfact-backlog `module-package.yaml`
- [ ] 5.2 Add CHANGELOG.md entry under Fixed
- [ ] 5.3 Commit with GPG signing: `git commit -S -m "fix: harden backlog daily export against HTML parsing edge cases"`
- [ ] 5.4 Push branch: `git push -u origin bugfix/backlog-html-export-validation`
- [ ] 5.5 Create PR to `dev`

## 6. Cleanup (post-merge)

- [ ] 6.1 Return to primary checkout: `cd /home/dom/git/nold-ai/specfact-cli-modules`
- [ ] 6.2 Remove worktree: `git worktree remove ../specfact-cli-worktrees/bugfix/backlog-html-export-validation`
- [ ] 6.3 Delete local branch: `git branch -d bugfix/backlog-html-export-validation`
- [ ] 6.4 Prune worktree list: `git worktree prune`
