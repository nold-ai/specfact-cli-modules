## Context

`specfact backlog map-fields` already persists provider mapping metadata that includes the custom field mapping file path, selected work item type, required fields by work item type, and allowed values for ADO. GitHub mapping also persists provider metadata used for write operations. The current write paths do not consistently consume that persisted state: `backlog add` still hardcodes a narrow set of canonical fields, and writeback commands assume provider-required metadata will be preserved without a shared validation step.

The user requirement is stronger than the merged ADO add fix: persisted mapping config must drive provider-required field resolution across backlog commands by default, and command-line inputs must only override that resolved state when explicitly supplied.

## Goals / Non-Goals

**Goals:**
- Introduce one shared provider-required field resolution path for backlog write commands.
- Default to persisted `backlog map-fields` config when determining required mapped provider fields.
- Support explicit command-line override of mapped provider fields.
- Prompt for missing required mapped values in interactive mode.
- Fail fast in non-interactive mode before provider calls when required mapped fields are unresolved or unset.

**Non-Goals:**
- Replacing `backlog map-fields` with a new configuration format.
- Adding provider-specific bespoke prompts for every field outside the shared mapping contract.
- Solving provider-side schema discovery beyond the metadata already persisted by `map-fields`.

## Decisions

### 1. Add a shared provider-required field resolver

Create a helper layer that takes:
- adapter/provider name
- persisted backlog provider settings and mapping file
- command-supplied canonical values
- command-supplied provider-field overrides
- current interactive/non-interactive mode

It returns:
- resolved canonical values
- provider-specific write payload fields
- validation errors for missing required mapped fields

Rationale: this prevents `backlog add`, refine import/writeback, and similar flows from each reimplementing partial provider-field logic.

### 2. Make `map-fields` config the default source of truth

Provider-required field metadata persisted by `map-fields` must be consulted first. Command-line canonical values and explicit provider-field overrides only replace the resolved defaults when present.

Rationale: the command should follow the already-configured enterprise mapping instead of assuming a fixed canonical field set.

### 3. Add a generic provider-field override option

Introduce a repeatable override input for backlog write commands, shaped so users can pass provider field/value pairs without editing config. This should be generic enough to work for both ADO and GitHub.

Rationale: some required fields are enterprise-specific and cannot be represented by the built-in canonical CLI flags alone.

Alternative considered: keep adding one canonical CLI option per new field. Rejected because it does not scale and still fails for arbitrary required provider fields.

### 4. Separate interactive prompting from non-interactive validation

Interactive flows should prompt only for provider-required fields that remain unresolved after config defaults and explicit overrides are applied. Non-interactive flows must return a clear validation error listing the missing mapped fields and the relevant provider config source.

Rationale: this preserves automation safety while keeping interactive usage viable for enterprise setups.

## Risks / Trade-offs

- [Scope growth] → Limit the first implementation to backlog commands that actually issue create/update provider writes in this repo, and centralize the resolver so more commands can adopt it incrementally.
- [Provider metadata gaps] → When `map-fields` has not persisted enough metadata, fail with a clear remediation message to rerun `specfact backlog map-fields` or pass explicit overrides.
- [CLI surface complexity] → Keep override syntax generic and repeatable rather than provider-specific.
- [Behavior changes in existing automation] → Preserve current canonical flags as overrides so existing scripts continue working.

## Migration Plan

- No data migration is required.
- Existing `map-fields` output remains the default config source.
- Backlog automation that already passes canonical CLI flags should continue to work, with the added ability to override mapped provider fields explicitly.

## Open Questions

- Which exact override syntax is least disruptive for Typer-based backlog commands while staying provider-agnostic?
- For GitHub required project fields, is the current persisted metadata sufficient to prompt users for missing values, or do we need to persist additional required-field details in `map-fields` output?
