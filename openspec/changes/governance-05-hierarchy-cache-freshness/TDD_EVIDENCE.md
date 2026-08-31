# TDD Evidence: governance-05-hierarchy-cache-freshness

- GitHub issue: [#457](https://github.com/nold-ai/specfact-cli-modules/issues/457), open/Todo on 2026-08-31; parent Feature #163; labels `bug`, `codebase`, `openspec`, and `change-proposal`; assignee `djm81`; SpecFact CLI project.
- Failing before implementation: `hatch run test tests/unit/scripts/test_sync_github_hierarchy_cache.py::test_sync_cache_skips_write_when_fingerprint_is_unchanged -q` started the repository-wide wrapper rather than honoring the focused selector. The added assertion requires `generated_at`, which the pre-change unchanged path omitted.
- Passing after implementation: `hatch run pytest tests/unit/scripts/test_sync_github_hierarchy_cache.py -q` -> `19 passed in 0.16s`.
- Quality: `hatch run format` -> pass; `hatch run lint scripts/sync_github_hierarchy_cache.py tests/unit/scripts/test_sync_github_hierarchy_cache.py` -> 0 errors, 0 warnings; `openspec validate governance-05-hierarchy-cache-freshness --strict` -> valid.
- Live verification: two successful runs on 2026-08-31 returned `Updated` then `unchanged` for the same 24-issue fingerprint. The unchanged run renewed `generated_at` from `2026-08-31T19:42:05Z` to `2026-08-31T19:42:28Z`.
