## Context

The modules docs site is a Jekyll site published at `modules.specfact.io`. Many authored pages set explicit `permalink` values such as `/bundles/code-review/overview/`, so browser URL resolution happens relative to the published permalink route rather than the source file path. Current validation has two separate surfaces: `tests/unit/docs/test_docs_review.py` performs several source-oriented link and front matter checks, while `scripts/check-docs-commands.py` validates command examples, selected cross-site routes, resource path drift, and navigation data. Both currently pass even when a published page has relative links that resolve to broken public URLs.

The current defect class is broader than the observed Code Review "See also" links. It includes docs command drift, body links that are only valid in source layout, incomplete front matter, docs dependency lockfile drift, and local/CI gates that treat docs-only changes as safe without running docs-specific validation locally.

## Goals / Non-Goals

**Goals:**

- Add a single category-based docs validation surface that can be used by scripts, tests, CI, and pre-commit without duplicated link-resolution logic.
- Validate authored docs links using published-page URL semantics so `/bundles/code-review/overview/` links are checked the same way a browser resolves them.
- Keep command-example validation aligned with the mounted module command surface and extend Code Review docs to cover current `specfact code review run` behavior.
- Make published docs front matter completeness a blocking check for all pages that publish as user-facing pages, with explicit exemptions only for documented redirect stubs if needed.
- Ensure docs build dependencies are installable before Pages deployment can be considered healthy.
- Route docs-only local changes through docs-specific validation rather than through a blanket "safe change" bypass.

**Non-Goals:**

- Do not redesign the documentation information architecture or rename public permalink routes beyond fixing broken links.
- Do not add network crawling of public production URLs as the primary validator; local generated route validation must be deterministic and usable before publishing.
- Do not change bundle runtime behavior or registry/signature metadata unless implementation discovers docs are generated directly from signed module payloads.
- Do not replace the existing Jekyll stack or migrate docs to a different static-site generator.

## Decisions

1. Build one reusable docs validation module and keep `scripts/check-docs-commands.py` as the CLI wrapper.

   - Rationale: current validation logic is split across tests and scripts, which allowed source-path checks and command checks to drift independently. A reusable helper can emit `ValidationFinding` records with stable categories such as `published-link`, `frontmatter`, `command`, `cross-site-link`, `nav-link`, and `docs-build-dependency`.
   - Alternative considered: extend only `tests/unit/docs/test_docs_review.py`. Rejected because CI logs and local scripts still need a direct validation command, and pre-commit should not depend on pytest-only helper internals.

2. Resolve body links against each page's published route, not against the source file directory.

   - Rationale: the public defect happens because links like `run/` from `/bundles/code-review/overview/` publish as `/bundles/code-review/overview/run/`. Validation must model the generated page URL and map the resolved route back to known Jekyll pages and redirect routes.
   - Alternative considered: require all links to be absolute. Rejected as too blunt; relative links can remain acceptable when they resolve correctly under published URL semantics.

3. Validate generated-site readiness with deterministic local checks first, and use Jekyll build/dependency install as a separate health gate.

   - Rationale: the link validator should catch route defects without needing a full Ruby environment, while `bundle install` and `jekyll build` catch dependency and generator failures. Keeping these as separate categories makes failures easier to diagnose.
   - Alternative considered: rely only on `bundle exec jekyll build`. Rejected because Jekyll can build pages that contain broken links, and dependency installation failures obscure content defects.

4. Treat front matter completeness as a published-page contract.

   - Rationale: missing `title`, `layout`, or `permalink` produces unstable navigation, search, redirects, and route inference. Existing "pre-existing warning" behavior hides debt and lets regressions pass.
   - Alternative considered: keep warning allowlists for old pages. Rejected because the current issue shows warning debt is indistinguishable from accepted behavior in CI.

5. Make docs-only local changes run docs checks, not contract/code-review checks.

   - Rationale: docs-only changes are safe from Python contract-test costs, but they are not safe from docs quality defects. Pre-commit should skip code-specific Block 2 only after running the docs validation appropriate for staged docs files.
   - Alternative considered: run full `docs-review` pytest suite in every pre-commit. Rejected as likely too slow; a targeted docs validation script can cover route/frontmatter/command categories quickly, with pytest and Jekyll build remaining CI/finalization gates.

6. Check Code Review docs parity with CLI option metadata by category, not just by fixed strings.

   - Rationale: option drift recurs when command flags change and docs are manually edited. Tests should compare the documented option table for `specfact code review run` against the current Typer command option surface for important public flags, including `--bug-hunt`, `--mode`, `--focus`, and `--level`.
   - Alternative considered: manually update the page and rely on review. Rejected because this was exactly the failure mode.

## Risks / Trade-offs

- [Risk] Strict published-route validation may surface many existing broken links at once. → Mitigation: implement the validator as category-based output, fix current failures in the same change, and only allow explicit, documented exemptions for intentional non-page links.
- [Risk] Jekyll relative-link plugins may rewrite some `.md` links differently from the simple route model. → Mitigation: validate both known source-to-route mappings and the built `_site` output when Ruby dependencies are available; prefer absolute published routes in ambiguous cases.
- [Risk] Adding Bundler/Jekyll install checks to local pre-commit would be too slow and network-dependent. → Mitigation: keep dependency install/build checks in CI and finalization, while pre-commit runs deterministic local route/frontmatter/command validation.
- [Risk] Centralizing docs validation could make the script too broad. → Mitigation: keep small, typed validators with stable category names and tests for each category.
- [Risk] Docs option parity tests may overfit to Typer formatting. → Mitigation: compare canonical option names from command definitions to documented table entries, not rendered help text formatting.

## Migration Plan

1. Add failing tests for published-route link validation using current broken Code Review overview links and at least one generated-route-safe example.
2. Add failing tests for front matter completeness using the currently incomplete redirect/guide pages.
3. Add failing tests for Code Review run option documentation parity.
4. Implement the shared docs validation helper and wire `scripts/check-docs-commands.py` through it.
5. Fix current docs link, front matter, and Code Review docs drift.
6. Update pre-commit scripts/config so docs-only staged changes run docs validation before being treated as safe for code-specific checks.
7. Update docs-review/docs-pages CI so generated-site checks and docs dependency install/build health are explicit and logged.
8. Run `openspec validate --strict`, docs validation, docs tests, Jekyll dependency/build checks, and targeted quality gates.

Rollback is straightforward: revert the docs validation helper, workflow/pre-commit wiring, and docs content fixes together. No persisted data migration or registry mutation is expected.

## Open Questions

- Should redirect-only stub pages require a `title`, or should a documented `redirect_stub: true`-style exemption be accepted for pages that never render meaningful content?
- Should the docs dependency installability check update `docs/Gemfile.lock` in this change, or should it only detect and fail the current stale lockfile until a separate dependency maintenance change updates it?
- Should generated `_site` link validation be mandatory in PR CI for all docs changes, or only in the Pages workflow plus explicit finalization gate?
