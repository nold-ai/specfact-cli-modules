# Implementation Tasks: bugfix-backlog-html-export-validation

## 1. Branch and worktree setup

- [ ] 1.1 Create worktree from origin/dev: `git worktree add ../specfact-cli-worktrees/bugfix/backlog-html-export-validation -b bugfix/backlog-html-export-validation origin/dev`
- [ ] 1.2 Change to worktree: `cd ../specfact-cli-worktrees/bugfix/backlog-html-export-validation`
- [ ] 1.3 Bootstrap Hatch environment: `hatch env create`
- [ ] 1.4 Verify pre-flight checks: `hatch run smart-test-status` and `hatch run contract-test-status`
- [ ] 1.5 Add spec delta to `openspec/changes/bugfix-backlog-html-export-validation/specs/backlog-daily-markdown-normalization/spec.md` for copilot-export consistency and hardening scenarios

## 2. Tests (TDD)

- [ ] 2.1 Add failing test: `_build_copilot_export_content` with `include_comments=True` and HTML comment produces Markdown-only output (no raw `<div>`, `<br>`)
- [ ] 2.2 Add failing test: `_normalize_markdown_text` with malformed HTML (e.g. `<div` without `>`) does not raise; returns stripped content
- [ ] 2.3 Add failing test: `_normalize_markdown_text` with very long input (> 50KB) does not hang (ReDoS guard)
- [ ] 2.4 Run tests and capture failing evidence in `TDD_EVIDENCE.md`

## 3. Implementation

- [ ] 3.1 Apply `_normalize_markdown_text` to comments in `_build_copilot_export_content` when `include_comments=True`
- [ ] 3.2 Add input length guard: truncate or skip normalization for inputs > 50KB before regex
- [ ] 3.3 Wrap `_normalize_markdown_text` call in try/except with fallback: `re.sub(r"<[^>]+>", "", html.unescape(str(text)))` on exception
- [ ] 3.4 Add defensive `str(c)` when iterating comments in export/summarize loops
- [ ] 3.5 Re-run tests and capture passing evidence in `TDD_EVIDENCE.md`

## 4. Quality gates

- [ ] 4.1 Run `hatch run format` and `hatch run type-check`
- [ ] 4.2 Run `hatch run contract-test` and `hatch run smart-test`

## 5. Documentation and validation

- [ ] 5.1 Update docs if `--copilot-export` behavior is documented (e.g. agile-scrum-workflows, backlog guides)
- [ ] 5.2 Run `openspec validate bugfix-backlog-html-export-validation --strict`

## 6. Version and PR

- [ ] 6.1 Bump patch version in `pyproject.toml`, `setup.py`, `src/specfact_cli/__init__.py` (specfact-cli); bump version in specfact-backlog `module-package.yaml` if changed
- [ ] 6.2 Add CHANGELOG.md entry under Fixed
- [ ] 6.3 Commit with GPG signing: `git commit -S -m "fix: harden backlog daily export against HTML parsing edge cases"`
- [ ] 6.4 Push branch: `git push -u origin bugfix/backlog-html-export-validation`
- [ ] 6.5 Create PR to `dev`

## 7. Cleanup (post-merge)

- [ ] 7.1 Return to primary checkout: `cd /home/dom/git/nold-ai/specfact-cli`
- [ ] 7.2 Remove worktree: `git worktree remove ../specfact-cli-worktrees/bugfix/backlog-html-export-validation`
- [ ] 7.3 Delete local branch: `git branch -d bugfix/backlog-html-export-validation`
- [ ] 7.4 Prune worktree list: `git worktree prune`
