# Spec-Kit Change Proposal Bridge

## Why

Users need to draft OpenSpec change proposals from spec-kit feature folders and synchronize backlog issues between spec-kit extensions and SpecFact. Currently OpenSpec natively creates change proposals (`openspec/changes/`), and spec-kit creates features (`specs/{feature}/spec.md + plan.md + tasks.md`), but there is no bridge to convert between these formats. Solo developers using spec-kit want to adopt SpecFact's structured change workflow without re-authoring specs. Teams want backlog issues created by spec-kit extensions (Jira, ADO, Linear, GitHub Projects) to sync into SpecFact's backlog tracking without duplicate creation. This change adds bidirectional conversion between spec-kit feature folders and OpenSpec change proposals, plus awareness of spec-kit backlog extension issue mappings.

## What Changes

- **Add spec-kit→OpenSpec change proposal conversion**: Convert a spec-kit feature folder (`specs/{feature}/spec.md`, `plan.md`, `tasks.md`) into an OpenSpec change proposal (`proposal.md`, `design.md`, `specs/`, `tasks.md`) with proper artifact mapping
- **Add OpenSpec→spec-kit feature export**: Convert an OpenSpec change proposal back to spec-kit feature folder format for roundtrip workflows
- **Add spec-kit backlog extension issue detection**: Detect when spec-kit extensions (Jira, ADO, Linear, GitHub Projects, Trello) have created issues from specs, and import those issue mappings to avoid duplicate creation during SpecFact backlog sync
- **Add `specfact sync bridge --adapter speckit --mode change-proposal` command variant**: New sync mode that operates on change proposals rather than plan bundles
- **Add profile-aware adapter behavior**: Solo profile uses spec-kit as primary authoring tool with SpecFact as enforcement layer; team profile enables reconciliation between both tools

## Capabilities

### New Capabilities

- `speckit-change-proposal-bridge`: Bidirectional conversion between spec-kit feature folders and OpenSpec change proposals, including artifact mapping and format translation
- `speckit-backlog-extension-sync`: Detection and import of issue mappings created by spec-kit backlog extensions to prevent duplicate issue creation during SpecFact sync

### Modified Capabilities

- `backlog-sync`: Extended to check for spec-kit backlog extension issue mappings before creating new issues

## Impact

- **Code**: `packages/specfact-project/src/specfact_project/sync_runtime/bridge_sync.py`, `packages/specfact-project/src/specfact_project/importers/speckit_converter.py`, `packages/specfact-project/src/specfact_project/sync/commands.py`
- **Tests**: New unit/integration tests for change proposal conversion and backlog extension detection
- **Docs**: `docs/guides/speckit-comparison.md` (add change proposal bridge), `docs/guides/integrations-overview.md` (update spec-kit integration section)
- **Dependencies**: Depends on `speckit-02-v04-adapter-alignment` in specfact-cli core (extension catalog detection, version detection)
- **Cross-repo**: Uses `ToolCapabilities.extension_commands` from core to detect backlog extensions

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #116
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/116>
- **Cross-repo dependency**: specfact-cli#453
- **Last Synced Status**: proposed
- **Sanitized**: false
