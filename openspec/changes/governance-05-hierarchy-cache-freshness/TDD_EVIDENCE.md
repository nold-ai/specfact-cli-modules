# TDD Evidence: governance-05-hierarchy-cache-freshness

- GitHub issue: [#457](https://github.com/nold-ai/specfact-cli-modules/issues/457), open/Todo on 2026-08-31; parent Feature #163; labels `bug`, `codebase`, `openspec`, and `change-proposal`; assignee `djm81`; SpecFact CLI project.
- Failing before implementation: in a detached worktree at PR base `14658da1024073d5d549ba69ad3f485cd3729204`, the direct command `hatch run pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py::test_sync_cache_skips_write_when_fingerprint_is_unchanged -q` failed with `KeyError: 'generated_at'` after adding the regression assertion. This proves the unchanged path omitted the freshness timestamp. The earlier repository-wide `hatch run test` wrapper did not honor the focused selector and is not used as failing-first evidence.
- Passing after implementation: `hatch run pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py -q` -> `27 passed in 0.29s` after the non-regular cache-path preservation review fix.
- Review-fix failing before implementation: `hatch run pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py::test_sync_cache_rewrites_invalid_markdown_despite_matching_state -q` -> failed because the prior unchanged path returned `changed=False` for a truncated markdown cache. The cache now verifies regular-file repository and fingerprint metadata before refreshing state.
- Latest review-fix failing before implementation: `hatch run pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py::test_sync_cache_rewrites_non_utf8_markdown_despite_matching_state -q` -> failed with `UnicodeDecodeError` before the cache could regenerate invalid UTF-8 bytes.
- Latest review-fix failing before implementation: `hatch run pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py -k 'symlinked or incomplete' -q` -> **2 failed**: a symlink path remained in place and a metadata-only cache returned `changed=False`.
- Latest review-fix failing before implementation: `hatch run pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py -k 'without_fetched or empty_directory' -q` -> **2 failed**: a cache missing fetched issue blocks returned `changed=False`, and an empty directory cache path raised `IsADirectoryError`.
- Latest review-fix failing before implementation: `hatch run pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py::test_sync_cache_preserves_non_empty_directory_cache_path -q` -> failed with `OSError: Directory not empty` before cache regeneration.
- Latest review-fix failing before implementation: `hatch run pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py::test_sync_cache_preserves_fifo_cache_path_before_writing -q` -> failed with `AssertionError: sync attempted to write to the FIFO`, proving the refresh reached the special path instead of replacing it.
- Code-review evidence: `SPECFACT_CLI_REPO=/Users/dom/git/nold-ai/specfact-cli-worktrees/bugfix/module-scope-02-preserve-user-installs hatch run python scripts/pre_commit_code_review.py scripts/sync_github_hierarchy_cache.py tests/unit/scripts/test_sync_github_hierarchy_cache.py` -> `PASS_WITH_ADVISORY`, changed-scope enforcement passed, and `.specfact/code-review.json` was generated. The advisory report contains pre-existing whole-file findings and a CrossHair dependency-isolation import failure; neither is introduced by this change.
- Quality: `SPECFACT_CLI_REPO=/Users/dom/git/nold-ai/specfact-cli-worktrees/bugfix/module-scope-02-preserve-user-installs hatch run format` -> pass; `SPECFACT_CLI_REPO=/Users/dom/git/nold-ai/specfact-cli-worktrees/bugfix/module-scope-02-preserve-user-installs hatch run lint scripts/sync_github_hierarchy_cache.py tests/unit/scripts/test_sync_github_hierarchy_cache.py` -> 0 errors, 0 warnings; `openspec validate governance-05-hierarchy-cache-freshness --strict` -> valid.
- Live verification: two successful runs on 2026-08-31 returned `Updated` then `unchanged` for the same 24-issue fingerprint. The unchanged run renewed `generated_at` from `2026-08-31T19:42:05Z` to `2026-08-31T19:42:28Z`.

## PR #464 publication review (2026-09-07, Europe/Berlin)

Base: `cd7fa371c79da69782bcd14accbd64e15c40a93d`.
The prior preservation check was followed by an independent truncating open.
The same sink existed for state writes on both changed and unchanged refreshes.
The fix publishes completed, private (0600) UTF-8 temporary files through atomic
replacement. POSIX operations remain anchored to one open parent directory;
the portable non-POSIX branch uses same-directory replacement. Existing
nonregular-entry preservation and unchanged markdown semantics remain intact.
This fixes publication, not every read-side filesystem validation boundary.

After specifying the invariant and before production edits:
`hatch run python -m pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py -q --no-cov -k 'never_opens_final or failed_publication or skips_write_when_fingerprint'`
returned **3 failed, 1 passed, 26 deselected**. Guards caught direct writes to
both final destinations; injected replacement failure was not reached.
No race or exploit was executed.

After implementation, the cache suite passed **30 tests**. Combined cache,
payload, and signed-installer suites passed **136 tests** on Python 3.12.13
and core 0.55.4. The timestamp regression now seeds an older state timestamp,
asserts it advances, and compares the complete original markdown bytes.
Format and lint/type checks passed (zero errors/warnings; Pylint 10/10).
Independent read-only patch review found no concrete surviving publication
bypass or refresh regression; its six benign controls passed. Native Windows
execution was not available. Parent-directory policy and read-side hardening
beyond publication are not claimed by this patch.

Full repository regression: `hatch run test -q` passed **1813 tests** in 86.26 seconds, with two external Lark deprecation warnings.

Final inspection added a static temporary-name collision control: it failed once
because cleanup removed an entry not created by this writer. Cleanup now requires
successful exclusive creation before unlinking. The strengthened timestamp and
collision controls preserve legitimate cached content without executing a race.
