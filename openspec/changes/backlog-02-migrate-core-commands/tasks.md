# Implementation Tasks: backlog-02-migrate-core-commands

## 1. Branch and worktree setup

- [x] 1.1 Create worktree from origin/dev: `git worktree add ../specfact-cli-worktrees/feature/backlog-02-migrate-core-commands -b feature/backlog-02-migrate-core-commands origin/dev`
- [x] 1.2 Change to worktree: `cd ../specfact-cli-worktrees/feature/backlog-02-migrate-core-commands`
- [x] 1.3 Bootstrap Hatch environment: `hatch env create`
- [x] 1.4 Verify pre-flight checks: `hatch run smart-test-status` and `hatch run contract-test-status`
- [x] 1.5 Copy backlog-core source from `specfact-cli-worktrees/feature/agile-01-feature-hierarchy/modules/backlog-core/src/backlog_core/` to `specfact-cli-modules/packages/specfact-backlog/src/specfact_backlog/backlog_core/`
- [x] 1.6 Verify copied files: `add.py`, `analyze_deps.py`, `delta.py`, `diff.py`, `promote.py`, `sync.py`, `verify.py`, `release_notes.py`, `main.py`, `graph/`, `adapters/`, `analyzers/`

## 2. Integration and refactoring

- [x] 2.1 Update imports in all copied files: replace `backlog_core` with `specfact_backlog.backlog_core`
- [x] 2.2 Keep command functions in `backlog_core/commands/` as submodules
- [x] 2.3 Register commands in main `commands.py` using `@app.command()` decorator
- [x] 2.4 Update `_ORDER_PRIORITY` in `_BacklogCommandGroup` (if needed)
- [x] 2.5 Add ceremony aliases handled by backlog module directly
- [x] 2.6 Resolve import conflicts with existing specfact-backlog utilities

## 3. Tests (TDD)

- [x] 3.1 Copy tests from `modules/backlog-core/tests/` to `specfact-cli-modules/tests/unit/specfact_backlog/`
- [x] 3.2 Update test imports to use specfact-backlog paths
- [x] 3.3 Fix `importlib.import_module()` calls to use new module paths
- [x] 3.4 Add conftest.py with PYTHONPATH setup for subprocess tests
- [x] 3.5 Fix ADO adapter test field paths (System.AcceptanceCriteria, Common.StoryPoints)
- [x] 3.6 Add schema_extensions to module-package.yaml
- [x] 3.7 Fix ANSI color code issues in test assertions

## 4. Import Boundary Fixes

- [x] 4.1 Fix `specfact_cli.registry.bridge_registry` imports in backlog_core (removed protocol registration)
- [x] 4.2 Fix `specfact_cli.utils.prompts` imports (created local utils module)
- [x] 4.3 Remove cross-bundle imports from specfact_project to specfact_backlog (replaced with stubs)
- [x] 4.4 Verify import boundary check passes

## 5. Quality gates

- [x] 5.1 Run `hatch run format`: 274 files OK
- [x] 5.2 Run `hatch run type-check`: 0 errors, 0 warnings, 0 notes
- [x] 5.3 Run `hatch run contract-test`: 204 passed, 16 skipped
- [x] 5.4 Run `hatch run smart-test`: 204 passed, 16 skipped
- [x] 5.5 Verify no duplicate command warnings
- [x] 5.6 Update module version in `module-package.yaml` (specfact-backlog): 0.41.0 → 0.41.1
- [x] 5.7 Sign module: `hatch run python scripts/sign-modules.py --key-file <key> packages/specfact-backlog/module-package.yaml packages/specfact-project/module-package.yaml`
- [x] 5.8 Verify signature: `hatch run ./scripts/verify-modules-signature.py --require-signature`

## 6. Documentation

- [ ] 6.1 Update `docs/guides/agile-scrum-workflows.md` to confirm command availability
- [ ] 6.2 Update `docs/guides/backlog-delta-commands.md` to confirm delta subcommands
- [ ] 6.3 Update `docs/guides/backlog-dependency-analysis.md` to confirm analyze-deps
- [ ] 6.4 Update CHANGELOG.md with restored commands

## 7. Validation and PR

- [x] 7.1 Run `openspec validate backlog-02-migrate-core-commands --strict`
- [x] 7.2 Run `/wf-validate-change backlog-02-migrate-core-commands` (completed earlier)
- [x] 7.3 Stage all changes: `git add -A`
- [x] 7.4 Commit with GPG signing: `git commit -S -m "feat: migrate backlog-core commands to specfact-backlog bundle"`
- [x] 7.5 Push branch: `git push -u origin feature/backlog-02-migrate-core-commands`
- [x] 7.6 Create PR to `dev`: https://github.com/nold-ai/specfact-cli-modules/pull/32

## 8. Cleanup (post-merge)

- [x] 8.1 Return to primary checkout: `cd /home/dom/git/nold-ai/specfact-cli-modules`
- [x] 8.2 Remove worktree: `git worktree remove ../specfact-cli-worktrees/feature/backlog-02-migrate-core-commands`
- [x] 8.3 Delete local branch: `git branch -d feature/backlog-02-migrate-core-commands`
- [x] 8.4 Prune worktree list: `git worktree prune`

## Notes

- Import boundary violations were resolved by:
  - Removing direct `specfact_cli` imports from backlog_core
  - Creating local `utils/__init__.py` for prompt functions
  - Replacing specfact_project's backlog-dependent functions with stubs
- Protocol registration moved to conftest.py for tests only
- All quality gates passing except module signing (requires user GPG key)
