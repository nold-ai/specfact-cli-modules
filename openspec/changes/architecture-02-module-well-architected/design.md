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

#### Implementation Requirements

Implementation PRs must include a complete `module-package.yaml` for the new specfact-architecture bundle and explicitly declare the adapter/manifest boundaries deferred by this decision. The package must define all required fields following the same pattern as specfact-govern/specfact-codebase:

- `name`, `version`, `commands`, `tier`, `publisher`
- `bundle_dependencies`, `pip_dependencies`
- `core_compatibility` (e.g., ">=0.40.0,<1.0.0") that matches the paired specfact-cli change
- `integrity`

Verification steps before merging:
- Confirm the `architecture-02-well-architected-review` entry exists and is stable in specfact-cli
- Verify registry integration by passing the existing `sign-modules-on-approval` and `publish-modules` workflows so manifests auto-sign and tarballs auto-publish

### 2. Treat boundary policies as portable rule resources

- **Decision**: Convert the `ALLOWED_IMPORTS.md` pattern into bundle-consumable rules/resources rather than reading only repository-local markdown ad hoc. The portable rule schema and enforcement code must preserve all three policy dimensions from ALLOWED_IMPORTS.md: (1) dual-mode prefix matching by adding a flag/field for exact+dot-prefix matching (preserving the `_is_allowed_prefix` semantics) so the rule parser and matcher honor it, (2) a MIGRATE-tier blocking marker or enforcement-level field that causes unconditional forbids for non-allowed imports in that tier, and (3) directional cross-bundle allowlists (explicit source→target allow entries) so bundle isolation rules are expressible. The rule parser/loader, matcher (where `_is_allowed_prefix` is referenced), and enforcement engine must read these fields and enforce them deterministically.
- **Why**: The bundle needs deterministic, reusable behavior across repositories while maintaining full enforcement fidelity from ALLOWED_IMPORTS.md.
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

1. Confirm the paired core architecture review contract (`architecture-02-well-architected-review`) is stable enough for module integration. **Meta-note**: This design can merge as a design artifact, but implementation PRs must verify the dependency checklist (presence of `architecture-02-well-architected-review` in `specfact-cli`, documented overlaps with `architecture-01-solution-layer`, and a stable paired core change) before any module integration or references are added.
2. Implement package structure, analyzer adapters, and rule-resource translation.
3. Publish docs, registry metadata, signatures, and compatibility range together.

## Dependency Checklist

**Implementation BLOCKER**: Module integration and any references to the contract named `architecture-02-well-architected-review` in the repository `specfact-cli` are disallowed until the paired `specfact-cli` change exists and is marked stable. Implementation PRs cannot proceed until the following conditions are met:

- [ ] The `architecture-02-well-architected-review` artifact exists in `specfact-cli` with a stable contract
- [ ] Overlaps and boundaries with `architecture-01-solution-layer` are documented and resolved
- [ ] The paired core change is marked as stable and available for module integration

## Open Questions

- Which dependency graph providers should be first-class on day one for Python and JavaScript repositories?
- Should interface diff support start with one ecosystem or ship as a provider abstraction from the first implementation?