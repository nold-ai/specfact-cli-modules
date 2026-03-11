## Context

`specfact backlog add` already resolves ADO work item type mappings from the custom field-mapping file, and `specfact backlog map-fields` already discovers the required custom fields for the selected work item type. The gap is in create payload construction: ADO create currently receives the resolved work item type, but not the mapped canonical custom fields that make the selected type valid for provider-side validation.

The change sits on an integration boundary. The module owns CLI payload assembly, while the downstream ADO adapter owns provider field emission. The design needs to keep those responsibilities aligned without introducing provider-specific prompt logic in interactive mode.

## Goals / Non-Goals

**Goals:**
- Build the same ADO create payload contract for interactive and non-interactive `backlog add` flows.
- Reuse existing field-mapping configuration instead of inventing a second ADO create schema.
- Add regression coverage for required mapped custom fields and work item type propagation.

**Non-Goals:**
- Redesign `map-fields` metadata discovery or ADO field-mapping persistence.
- Change GitHub create payload behavior.
- Implement provider adapter changes in repositories outside `specfact-cli-modules`.

## Decisions

### Decision: Treat ADO create payload assembly as mapping-driven, not prompt-driven

`backlog add` should derive ADO provider fields from the resolved custom mapping file after interactive and non-interactive inputs have been normalized into the same canonical payload. This keeps both invocation modes behaviorally equivalent and avoids a class of bugs where only one path enriches the provider payload.

Alternative considered:
- Build separate interactive-only enrichment logic from prompt selections.
This was rejected because it duplicates mapping logic and would reintroduce parity drift.

### Decision: Preserve the explicit `work_item_type` contract and extend it with mapped fields

The existing explicit `work_item_type` payload should remain, because downstream ADO create handling already depends on it. The change should add mapped provider fields alongside that contract rather than replacing it, so the adapter can continue deciding how to serialize the request while receiving the full required field set.

Alternative considered:
- Collapse work item type into provider fields only.
This was rejected because it would make the current adapter contract less explicit and risk regressions in already-fixed work item type mapping behavior.

### Decision: Capture parity with focused unit tests at the command boundary

Regression tests should assert the payload emitted by `backlog add` for ADO create, including required custom fields and work item type resolution. This is the narrowest place to prove parity between interactive and non-interactive command flows inside this repository.

Alternative considered:
- Rely only on adapter integration tests.
This was rejected because the bug originates before the downstream provider request is built.

## Risks / Trade-offs

- [Risk] The downstream ADO adapter may ignore newly supplied mapped fields even if the module forwards them. → Mitigation: document the adapter boundary in the proposal and validation report so any remaining gap is explicit.
- [Risk] Field mappings may include canonical keys that are not user-supplied during create. → Mitigation: limit create-time emission to resolved values that are present or required by configured mappings and cover the expected payload shape in tests.
- [Risk] Existing ADO projects with partial mapping files may depend on fallback behavior. → Mitigation: preserve current fallback behavior when no custom mapping file or mapped value is available.
