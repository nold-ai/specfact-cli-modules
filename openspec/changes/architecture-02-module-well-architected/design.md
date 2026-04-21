# Architecture Well-Architected Module Design

## Context

Architecture governance spans both shared contracts in `specfact-cli` and executable repository analysis in `specfact-cli-modules`. This change defines the module bundle that inspects dependency boundaries, interface changes, and ADR traceability while mapping results into the paired core architecture review model.

## Goals / Non-Goals

**Goals:**

- Define the package structure and command ownership for `specfact-architecture`.
- Reuse repository boundary patterns such as `ALLOWED_IMPORTS.md` instead of inventing a second mechanism.
- Normalize architecture findings into the paired core report contract for downstream policy and evidence flows.
- Keep bundle dependencies explicit and optional by analyzer/provider.

**Non-Goals:**

- Reimplement the paired core architecture scoring or findings schema.
- Replace hand-written ADR content or lifecycle management.
- Introduce enterprise-only policy-server behavior in the first release.

## Decisions

### 1. Ship architecture review as a standalone official bundle

- **Decision**: Create `packages/specfact-architecture/` with the `architecture` command and its own manifest/signing lifecycle.
- **Why**: Architecture review spans different analyzers, docs, and adoption concerns than existing bundles.
- **Alternative considered**: Extend `specfact-govern` or `specfact-code-review`. Rejected because it would blur ownership and bundle identity.

### 2. Treat boundary policies as portable rule resources

- **Decision**: Convert the `ALLOWED_IMPORTS.md` pattern into bundle-consumable rules/resources rather than reading only repository-local markdown ad hoc.
- **Why**: The bundle needs deterministic, reusable behavior across repositories.
- **Alternative considered**: Hard-code modules-repo-specific checks. Rejected because it would not generalize to user repositories.

### 3. Separate graph extraction from policy evaluation

- **Decision**: Analyzer adapters extract imports/interfaces/ADR references first, then evaluate those facts through rule resources mapped to the paired core findings model.
- **Why**: This keeps the bundle adaptable across languages/toolchains while preserving one reporting contract.
- **Alternative considered**: Bind each analyzer directly to final findings. Rejected because it makes provider changes harder and duplicates evaluation logic.

## Risks / Trade-offs

- **Risk**: Cross-language dependency graphs vary in precision. → **Mitigation**: define provider-specific fixtures and make unsupported ecosystems degrade gracefully.
- **Risk**: Rule translation from `ALLOWED_IMPORTS.md` may miss nuanced intent. → **Mitigation**: specify a canonical rule-resource format and document where human review remains required.
- **Risk**: Interface diff analysis may create noisy findings. → **Mitigation**: make breaking/non-breaking classification explicit in scenarios and tests.

## Migration Plan

1. Confirm the paired core architecture review contract (`architecture-02-well-architected-review`) is stable enough for module integration. **Note**: A new core change `architecture-02-well-architected-review` must be created and synced into `specfact-cli` before module integration. This contract should clarify overlap with `architecture-01-solution-layer` regarding shared architecture review semantics and boundaries.
2. Implement package structure, analyzer adapters, and rule-resource translation.
3. Publish docs, registry metadata, signatures, and compatibility range together.

## Open Questions

- Which dependency graph providers should be first-class on day one for Python and JavaScript repositories?
- Should interface diff support start with one ecosystem or ship as a provider abstraction from the first implementation?