# Change: OpenSpec and Spec Kit Import Runtime for Requirement Evidence

## Why

OpenSpec and Spec Kit own upstream planning and specification authoring. The
modules repo provides the runtime that imports their native artifacts into
SpecFact requirement evidence, so the `specfact requirements` command group is
useful without hand-authored records files. Core owns the parsing,
normalization, hashing, and gate contracts; this module wires them to commands.

## Rescope (2026-07-13)

The previous scope (optional `## Intent Trace` YAML block, schema validation of
hand-authored metadata) is retired: SpecFact must not define an authoring
schema for upstream tools. New scope is **import-first**: parse native OpenSpec
change folders and Spec Kit feature folders as they exist today, read-only,
with deterministic pass/fail validation gates. See the core counterpart
proposal (nold-ai/specfact-cli#350) for contract details.

## Ownership Alignment (2026-07-13)

- Modules-owned scope retained here: `requirements import` runtime flags
  (`--from-openspec`, `--from-speckit`), source auto-detection, command wiring,
  and surfacing of gate findings in validate/list/coverage output.
- Core-owned scope remains: artifact parsers, normalization into
  `RequirementInput`, content-hash staleness contract, and gate evaluation.
- Runtime MUST stay thin: no parsing, hashing, or gate logic in this module.
- Runtime MUST NOT create or mutate upstream OpenSpec or Spec Kit artifacts.

## What Changes

- **NEW**: `specfact requirements import --from-openspec [PATH]` imports native
  OpenSpec change folders through the core evidence adapter.
- **NEW**: `specfact requirements import --from-speckit [PATH]` imports native
  Spec Kit feature folders through the core evidence adapter.
- **NEW**: Omitted paths auto-detect conventional layouts (`openspec/changes/`
  and Spec Kit `specs/`) relative to the project root.
- **EXTEND**: `requirements validate` surfaces the core gate findings
  (`scenario-unverified`, `stale-import`, `source-missing`,
  `ambiguous-mapping`, `unsupported-source-schema`) with profile-driven severity and non-zero exit on
  failure; `list`/`coverage` output includes gate-relevant counts.
- **EXTEND**: When `--profile` is omitted, the effective profile resolves from
  the layered configuration shipped by `profile-01-config-layering` instead of
  a hardcoded `startup` default; an explicit flag always wins.
- **EXTEND**: Preserve the core adapter's evidence-compatible required-field
  mapping (`id`, `title`, `acceptance`, and `trace_links`) and surface its
  `unsupported-profile-field` advisories unchanged. The module does not add
  owner, risk, or exception metadata to imported records.
- **EXTEND**: Surface core `unsupported-source-schema` errors unchanged and do
  not persist any partial import when core rejects an untested OpenSpec schema
  or a customized Spec Kit template profile.
- **UNCHANGED**: `--from-file` remains for generic records; existing sidecar
  persistence and merge semantics are reused as-is.

## Capabilities

### Modified Capabilities

- `requirements-module`: Runtime commands gain OpenSpec and Spec Kit import
  sources and gate-finding surfacing.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #168
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/168>
- **Core Counterpart**: nold-ai/specfact-cli#350
- **Last Synced Status**: open / Todo (aligned 2026-07-13)
- **Sanitized**: false
