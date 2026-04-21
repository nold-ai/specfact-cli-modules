# Design: security-02-module-license-compliance

## Context

License governance sits at the boundary of supply-chain security and legal compliance, but the runtime bundle needs to stay narrow enough that organizations can adopt it independently. This change defines the modules-side package that consumes SBOM data, evaluates SPDX license identifiers against policy, and reports findings through the shared core contracts.

## Goals / Non-Goals

**Goals:**

- Define the bundle structure and command ownership for `specfact-license-compliance`.
- Normalize SBOM/license evidence into the shared core findings model.
- Keep license exceptions and policy semantics aligned with existing policy/profile infrastructure.
- Make room for interoperability with the broader security bundle without forcing runtime consolidation.

**Non-Goals:**

- Replace the general-purpose security bundle for SAST, SCA, or secret scanning.
- Implement legal workflow tooling outside SpecFact’s findings/report surfaces.
- Introduce enterprise-only policy resolution in the bundle itself.

## Decisions

### 1. Ship license compliance as a sibling bundle

- **Decision**: Create a standalone `specfact-license-compliance` bundle instead of folding SPDX checks into `specfact-security`.
- **Why**: License policy often has different adoption, ownership, and exception flows than scanner-driven security review.
- **Alternative considered**: Add license scanning to the security bundle. Rejected because it would entangle release cadence and user scope.

### 2. Consume SBOM inputs rather than redefining package inventory

- **Decision**: The bundle can generate or ingest SBOM data, but its contract starts at normalized SBOM/license records instead of owning repository inventory logic.
- **Why**: SBOM generation backends may evolve independently while the bundle’s stable value is policy evaluation.
- **Alternative considered**: Make the bundle responsible for all dependency discovery semantics. Rejected because it duplicates security-bundle concerns.

### 3. Express license state through the core findings contract

- **Decision**: License allow/deny/exception outcomes map into the paired core findings model and report surfaces.
- **Why**: Downstream policy, evidence, and future enterprise reporting should not special-case license output.
- **Alternative considered**: Emit a separate license-only schema. Rejected because it fragments governance surfaces.

## Risks / Trade-offs

- **Risk**: SPDX normalization differences across SBOM tools may create inconsistent results. → **Mitigation**: define adapter fixtures and canonical SPDX mapping tables in tests.
- **Risk**: Users may expect the security bundle alone to cover license policy. → **Mitigation**: document bundle boundaries and integration points clearly.
- **Risk**: Exception handling can drift from core policy semantics. → **Mitigation**: rely on shared policy-pack interpretation instead of bundle-local exception logic.

## Migration Plan

1. Confirm paired core security/policy contracts are stable enough for integration.
2. Implement package structure, SBOM ingestion, and license evaluation adapters.
3. Publish manifest, registry, docs, and signatures together once compatibility is validated.

## Open Questions

- Should the first release generate SBOMs itself, consume shared SBOM artifacts, or support both modes from day one?
- Which SPDX edge cases need explicit normalization rules in the initial release?