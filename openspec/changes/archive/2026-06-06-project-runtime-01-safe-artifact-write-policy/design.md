## Context

The existing proposal assumed that many bundle runtime commands directly mutate user-owned repository files and therefore need a generic runtime safe-write layer. The current codebase and intended product model are narrower: bundle runtime code should normally keep its local artifacts under `.specfact/`, with only a small number of sanctioned external touchpoints outside `.specfact` such as IDE or prompt-related files.

That changes the practical design boundary. The paired core change defines safe handling for user-owned project artifacts outside `.specfact`, but it does not currently expose a broad generic runtime artifact API for arbitrary YAML, Markdown, or bundle-specific local files. This modules-side change therefore needs to separate two concerns:

- external user-owned artifacts outside `.specfact`, which should reuse core safe-write semantics
- SpecFact-managed artifacts inside `.specfact`, which need clear ownership rules but not the full core trust-boundary machinery

## Goals / Non-Goals

**Goals:**
- Reuse the paired core safe-write contract only for sanctioned runtime touchpoints outside `.specfact`.
- Standardize how bundle commands classify `.specfact` artifacts as fully owned state or merge-preserve config.
- Add a practical first-adopter scope in the backlog bundle where local writes are real and user-facing.
- Add tests that prove partially user-tuned `.specfact` config survives supported updates and external user-owned paths are not silently overwritten.

**Non-Goals:**
- Refactor every `write_text` call in the repo regardless of path, ownership, or risk.
- Invent a second generic runtime safe-write framework in `specfact-cli-modules` while core remains narrower.
- Treat all `.specfact` files as user-owned artifacts that require the full profile-04 policy.
- Change upstream provider writeback semantics; GitHub/ADO issue updates remain a separate concern.

## Decisions

### 1. External user-owned artifacts outside `.specfact` are the exception path and SHALL reuse core semantics

Bundle code already imports `specfact_cli` surfaces where needed. When a modules runtime command touches a sanctioned external user-owned artifact outside `.specfact`, it should reuse the paired core safe-write semantics rather than define a competing contract.

Rationale:
- One contract, one enforcement surface.
- Matches the actual user trust boundary.

Alternative considered:
- Create a modules-local generic safe-write abstraction for all runtime files. Rejected because the core API is not yet broad enough to justify a mirrored abstraction here.

### 2. `.specfact` artifacts SHALL use an ownership-aware policy rather than the full external safe-write contract

The first slice should distinguish between:

- fully owned generated state inside `.specfact` that SpecFact may recreate or replace deterministically
- merge-preserve config inside `.specfact` where users may tune unrelated provider settings or metadata and expect those values to survive targeted updates

Rationale:
- `.specfact` is the normal home for bundle runtime state.
- The main practical risk inside `.specfact` is accidental replacement of unrelated config, not arbitrary mutation of user-owned source files.

Alternative considered:
- Treat every `.specfact` artifact as a user-owned external file requiring the full core policy. Rejected because it adds heavy machinery where deterministic managed ownership is the intended model.

### 3. First adopters should come from the backlog bundle, not from speculative repo-wide writers

The most practical current paths are backlog config and mapping files under `.specfact`, plus sync-managed local state and explicit baseline/output paths. These paths are both real in the codebase and close to the change’s `backlog-add` and `backlog-sync` deltas.

Rationale:
- They cover real current behavior rather than hypothetical future writers.
- They let the change prove both merge-preserve config behavior and owned-state behavior.

Alternative considered:
- Start with `specfact-project` and `specfact-spec` writers broadly. Rejected because those paths mix generated files, temp artifacts, and future workflow design that is not yet bounded by a generic core API.

### 4. Modules-side verification should focus on behavior tests, not a second generic unsafe-write scanner

Rationale:
- The static “unsafe write” rule belongs with the core external safe-write contract boundary.
- This repo needs tests that prove local ownership behavior for selected bundle commands, not a second policy engine that will drift.

## Risks / Trade-offs

- `[Risk]` The change name still reads broader than the refined scope. → Mitigation: clarify the boundary explicitly in proposal/specs/design/tasks and keep the current id only for continuity.
- `[Risk]` `.specfact` config files can still contain user-tuned content that is easy to clobber. → Mitigation: require merge-preserve behavior for partially owned config and add regression fixtures around unrelated keys and sections.
- `[Risk]` Future modules runtime features may need a truly generic safe-write API from core. → Mitigation: defer broad repo-wide adoption until core exposes that surface; keep this change practical and backlog-focused.

## Migration Plan

1. Refresh this change’s artifacts to narrow scope to sanctioned external touchpoints and `.specfact` ownership boundaries.
2. Implement first-adopter backlog bundle behavior around config, mapping, and sync-managed local files.
3. Reuse core profile-04 behavior only where a modules command truly touches a user-owned path outside `.specfact`.
4. Defer any broader generic runtime safe-write abstraction to a follow-up that is paired with an expanded core API.

Rollback strategy:
- If a merge-preserve path proves unstable, fall back to fail-safe handling for that config mutation rather than broadening raw overwrite behavior.

## Open Questions

- Should the change id eventually be renamed to better reflect artifact boundaries rather than “safe write policy,” or is clarified content sufficient?
- Which external user-owned touchpoints outside `.specfact` still exist in modules runtime today beyond future prompt or IDE-oriented flows?
