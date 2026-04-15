## Why

Recent Code Review bundle changes added `specfact code review run` behavior and options that are not consistently documented on the bundle deep-dive pages, and published module overview pages contain links that pass source-file checks while breaking after Jekyll publishes them under permalink routes. This slipped through because the current docs and pre-commit gates validate selected source-path and command categories, but do not systematically validate generated-page URL semantics, required front matter completeness, docs build dependency health, or docs drift caused by command option changes.

## What Changes

- Update Code Review docs so the overview, run guide, and module notes consistently document the current command behavior, including `--bug-hunt`, `--mode shadow|enforce`, `--focus`, `--level`, progress output, JSON output, and invalid option combinations.
- Fix module overview and related deep-dive links so authored docs use published-route-safe links, especially "See also" sections under `/bundles/<bundle>/overview/`.
- Harden docs validation to check internal links as they resolve from the generated public page URL, not only as source-file-relative Markdown paths.
- Promote docs front matter checks from partial warning/allowlist behavior to category-based blocking rules for published pages, including required `layout`, `title`, and `permalink` keys or explicit documented exemptions for non-page redirects.
- Add or extend validation coverage for docs build dependency health so stale `docs/Gemfile.lock` entries cannot silently leave local or CI Pages builds unable to install.
- Integrate the stricter docs validation into local and CI gates so docs-only changes are not treated as "safe" without running docs-specific checks.
- Keep the solution category-based: detect broken published routes, incomplete front matter, command documentation drift, and build dependency drift as classes of findings instead of adding checks only for the currently observed Code Review links.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `modules-docs-command-validation`: Expand docs validation from command examples, legacy resources, selected core-doc handoffs, and nav URLs to generated-page link semantics, front matter completeness, and docs build dependency installability.
- `bundle-overview-pages`: Require overview-page "See also" and related links to resolve under the published permalink route, not just source file layout.
- `modules-docs-publishing`: Require independently publishable docs to include installable build dependencies and generated-site link validation before release or Pages deployment.
- `review-run-command`: Require Code Review command docs to stay aligned with the current `specfact code review run` option surface and behavior.
- `modules-pre-commit-quality-parity`: Require pre-commit and local quality scripts to run docs-specific validation for docs-only changes instead of skipping all second-stage checks as safe.

## Impact

- Affected docs include `docs/bundles/code-review/overview.md`, `docs/bundles/code-review/run.md`, `docs/modules/code-review.md`, bundle overview pages, and any published docs pages with relative links or incomplete front matter.
- Affected validation code includes `tests/unit/docs/test_docs_review.py`, `scripts/check-docs-commands.py`, docs validation tests, and potentially a dedicated reusable docs validation helper if consolidation is needed.
- Affected CI and local gates include `.github/workflows/docs-review.yml`, `.github/workflows/docs-pages.yml`, `.github/workflows/pr-orchestrator.yml`, `.pre-commit-config.yaml`, and `scripts/pre-commit-quality-checks.sh`.
- The current investigation found no docs page entirely missing front matter, but found five published guide redirect pages missing `title` metadata, current docs checks passing despite broken published-route links, and `bundle install --path vendor/bundle` blocked by the checked-in docs lockfile because `public_suffix 7.0.5` cannot be resolved from RubyGems.
- No bundle version, registry entry, module manifest, or signed module payload change is expected unless implementation discovers that docs are generated from package metadata that must move with a module release.

## Source Tracking

- GitHub Issue: [#202](https://github.com/nold-ai/specfact-cli-modules/issues/202)
- Parent Feature: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163)
- Parent Epic: [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162)
- Project: SpecFact CLI (`Todo`)
- Labels: `bug`, `documentation`, `codebase`, `openspec`, `change-proposal`, `enhancement`
- Blockers: none known
- Blocked by: none known
