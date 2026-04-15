# OpenSpec change order by module and dependency

## Implemented (archived)

| Change | Status / Date |
|--------|---------------|
| ✅ backlog-02-migrate-core-commands | archived 2026-03-10 |
| ✅ backlog-bundle-local-source-alignment | archived 2026-03-10 |
| ✅ bugfix-backlog-html-export-validation | archived 2026-03-10 |
| ✅ modules-pre-commit-quality-parity | archived 2026-03-10 |
| ✅ registry-republish-outdated-bundles | archived 2026-03-10 |
| ✅ fix-issue-49-ado-provider-field-type-coercion | archived 2026-03-11 |
| ✅ code-review-02-ruff-radon-runners | archived 2026-03-17 |
| ✅ code-review-04-contract-test-runners | archived 2026-03-17 |
| ✅ code-review-07-house-rules-skill | archived 2026-03-17 |
| ✅ code-review-08-review-run-integration | archived 2026-03-17 |
| ✅ code-review-10-review-scope-modes | archived 2026-03-17 |
| ✅ docs-01-modules-docs-canonical-site | archived 2026-03-17 |
| ✅ fix-backlog-add-ado-custom-field-payload | archived 2026-03-17 |
| ✅ fix-backlog-add-work-item-type-mapping | archived 2026-03-17 |
| ✅ fix-backlog-provider-required-field-mappings | archived 2026-03-17 |
| ✅ review-run-dogfood-followup | archived 2026-03-17 |
| ✅ docs-cli-command-alignment | archived 2026-03-20 |
| ✅ docs-06-modules-site-ia-restructure | archived 2026-04-05 |
| ✅ docs-08-bundle-overview-pages | archived 2026-04-05 |
| ✅ docs-09-missing-command-docs | archived 2026-04-05 |
| ✅ docs-10-workflow-consolidation | archived 2026-04-05 |
| ✅ docs-11-team-enterprise-tier | archived 2026-04-05 |
| ✅ docs-12-docs-validation-ci | archived 2026-04-05 |
| ✅ clean-code-02-expanded-review-module | archived 2026-04-05 |
| ✅ docs-13-nav-search-theme-roles | archived 2026-04-05 |
| ✅ speckit-03-change-proposal-bridge | archived 2026-04-05 |
| ✅ packaging-01-bundle-resource-payloads | archived 2026-04-05 |
| ✅ module-bundle-deps-auto-install | archived 2026-04-05 |
| ✅ governance-03-github-hierarchy-cache | archived 2026-04-09 |

## Pending

### Backlog bundle runtime changes

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| backlog-scrum | 02 | backlog-scrum-02-sprint-planning | [#160](https://github.com/nold-ai/specfact-cli-modules/issues/160) | Parent Feature: [#151](https://github.com/nold-ai/specfact-cli-modules/issues/151); shared backlog baseline from `specfact-cli#116` |
| backlog-scrum | 03 | backlog-scrum-03-story-complexity | [#153](https://github.com/nold-ai/specfact-cli-modules/issues/153) | Parent Feature: [#151](https://github.com/nold-ai/specfact-cli-modules/issues/151); shared backlog baseline from `specfact-cli#116` |
| backlog-scrum | 04 | backlog-scrum-04-definition-of-done | [#152](https://github.com/nold-ai/specfact-cli-modules/issues/152) | Parent Feature: [#151](https://github.com/nold-ai/specfact-cli-modules/issues/151); shared backlog baseline from `specfact-cli#116`; optional ceremony alias baseline `specfact-cli#185` |
| backlog-kanban | 01 | backlog-kanban-01-flow-metrics | [#155](https://github.com/nold-ai/specfact-cli-modules/issues/155) | Parent Feature: [#149](https://github.com/nold-ai/specfact-cli-modules/issues/149); shared backlog baseline from `specfact-cli#116` |
| backlog-safe | 01 | backlog-safe-01-pi-planning | [#154](https://github.com/nold-ai/specfact-cli-modules/issues/154) | Parent Feature: [#146](https://github.com/nold-ai/specfact-cli-modules/issues/146); shared backlog baseline from `specfact-cli#116` |
| backlog-safe | 02 | backlog-safe-02-risk-rollups | [#156](https://github.com/nold-ai/specfact-cli-modules/issues/156) | Parent Feature: [#146](https://github.com/nold-ai/specfact-cli-modules/issues/146); `#154`; integrates with `#160`, `#153`, and `#155` |
| policy | 02 | policy-02-packs-and-modes | [#158](https://github.com/nold-ai/specfact-cli-modules/issues/158) | Parent Feature: [#148](https://github.com/nold-ai/specfact-cli-modules/issues/148); shared policy/profile semantics from `specfact-cli#176` and `specfact-cli#237` |
| ceremony | 02 | ceremony-02-requirements-aware-output | [#159](https://github.com/nold-ai/specfact-cli-modules/issues/159) | Parent Feature: [#150](https://github.com/nold-ai/specfact-cli-modules/issues/150); requirements contracts from `specfact-cli#239`; ceremony alias baseline `specfact-cli#185` |

### Project bundle runtime changes

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| sync | 01 | sync-01-unified-kernel | [#157](https://github.com/nold-ai/specfact-cli-modules/issues/157) | Parent Feature: [#147](https://github.com/nold-ai/specfact-cli-modules/issues/147); preview/apply safety baseline from `specfact-cli#177` |
| project-runtime | 01 | project-runtime-01-safe-artifact-write-policy | [#177](https://github.com/nold-ai/specfact-cli-modules/issues/177) | Parent Feature: [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161); paired core change [specfact-cli#490](https://github.com/nold-ai/specfact-cli/issues/490); related bug [specfact-cli#487](https://github.com/nold-ai/specfact-cli/issues/487) |

### Cross-layer runtime follow-ups

These changes are the modules-side runtime companions to split core changes. Shared schemas, contracts, and cross-change semantics remain in `specfact-cli`.

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| architecture | 01 | architecture-01-solution-layer | [#164](https://github.com/nold-ai/specfact-cli-modules/issues/164) | Parent Feature: [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161); core counterpart `specfact-cli#240`; shared models from `specfact-cli#238` and `specfact-cli#239` |
| requirements | 02 | requirements-02-module-commands | [#165](https://github.com/nold-ai/specfact-cli-modules/issues/165) | Parent Feature: [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161); core counterpart `specfact-cli#239`; data model baseline `specfact-cli#238` |
| requirements | 03 | requirements-03-backlog-sync | [#166](https://github.com/nold-ai/specfact-cli-modules/issues/166) | Parent Feature: [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161); core counterpart `specfact-cli#244`; runtime sync `#157`; requirements runtime `#165` |
| openspec | 01 | openspec-01-intent-trace | [#168](https://github.com/nold-ai/specfact-cli-modules/issues/168) | Parent Feature: [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161); core counterpart `specfact-cli#350`; requirements contracts from `specfact-cli#238` and `specfact-cli#239` |
| traceability | 01 | traceability-01-index-and-orphans | [#170](https://github.com/nold-ai/specfact-cli-modules/issues/170) | Parent Feature: [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161); core counterpart `specfact-cli#242`; runtime inputs from `#164` and `#165` |

### Validation and governance runtime follow-ups

These changes are the modules-side runtime companions to split core governance and validation changes. Core remains authoritative for schemas and CI/evidence contracts.

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| governance | 01 | governance-01-evidence-output | [#169](https://github.com/nold-ai/specfact-cli-modules/issues/169) | Parent Feature: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163); core counterpart `specfact-cli#247`; validation runtime `#171` |
| governance | 02 | governance-02-exception-management | [#167](https://github.com/nold-ai/specfact-cli-modules/issues/167) | Parent Feature: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163); core counterpart `specfact-cli#248`; policy runtime `#158` |
| governance | 04 | governance-04-deterministic-agent-governance-loading | [#181](https://github.com/nold-ai/specfact-cli-modules/issues/181) | Parent Feature: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163); paired core [specfact-cli#494](https://github.com/nold-ai/specfact-cli/issues/494); baseline [#178](https://github.com/nold-ai/specfact-cli-modules/issues/178) (implements archived `governance-03-github-hierarchy-cache`, paired core [specfact-cli#491](https://github.com/nold-ai/specfact-cli/issues/491)) |
| validation | 02 | validation-02-full-chain-engine | [#171](https://github.com/nold-ai/specfact-cli-modules/issues/171) | Parent Feature: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163); core counterpart `specfact-cli#241`; runtime inputs from `#164` and `#165`; policy semantics from `#158` |

### Code review and sidecar validation improvements

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| code-review + codebase | 01 | code-review-bug-finding-and-sidecar-venv-fix | [#174](https://github.com/nold-ai/specfact-cli-modules/issues/174) | Parent Feature: [#175](https://github.com/nold-ai/specfact-cli-modules/issues/175); Epic: [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162) |

### Module trust chain and CI security

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| marketplace | 06 | marketplace-06-ci-module-signing | [#185](https://github.com/nold-ai/specfact-cli-modules/issues/185) | Parent Feature: [#187](https://github.com/nold-ai/specfact-cli-modules/issues/187); Parent Epic: [#186](https://github.com/nold-ai/specfact-cli-modules/issues/186); paired core [specfact-cli#500](https://github.com/nold-ai/specfact-cli/issues/500) |

### Documentation restructure

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| docs | 14 | docs-14-module-release-history | [#124](https://github.com/nold-ai/specfact-cli-modules/issues/124) | docs-13 ✅; publish-modules workflow |

### Packaging and bundle payloads

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| packaging | 01 | ✅ packaging-01-bundle-resource-payloads (archived 2026-04-05) | [#101](https://github.com/nold-ai/specfact-cli-modules/issues/101) | — |

### Module bundle peer dependencies

| Module | Order | Change folder | GitHub # | Blocked by |
|--------|-------|---------------|----------|------------|
| peer-deps | 01 | ✅ module-bundle-deps-auto-install (archived 2026-04-05) | [#135](https://github.com/nold-ai/specfact-cli-modules/issues/135) | — |
