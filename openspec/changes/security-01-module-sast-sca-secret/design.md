# Context

Security analysis in the modules repo must package third-party scanners while deferring canonical findings, severity scoring, and policy interpretation to the core repo. This change establishes the bundle boundary for the broadest security surface: source-code analysis, dependency risk, SBOM generation, and secret detection. The bundle has to remain composable with license and privacy modules instead of becoming a catch-all for every security-adjacent concern.

## Goals / Non-Goals

**Goals:**

- Define the package structure and command ownership for a new `specfact-security` bundle.
- Normalize multiple analyzer outputs into the shared core security finding model.
- Keep policy-mode interpretation aligned with existing policy/profile work rather than inventing bundle-local severity logic.
- Make registry, manifest, and signing consequences explicit before implementation.

**Non-Goals:**

- Implement GDPR-specific privacy detection; that belongs in `security-03-module-pii-gdpr-eu`.
- Implement SPDX-focused license policy evaluation; that belongs in `security-02-module-license-compliance`.
- Replace the paired core security findings contract.

## Decisions

### 1. Keep broad security orchestration in one bundle

- **Decision**: SAST, SCA, SBOM, and secret scanning ship together in `specfact-security`.
- **Why**: These scanners are typically invoked in one review pass and share the same normalized findings pipeline.
- **Alternative considered**: Separate bundles for each scanner class. Rejected because it would fragment the default security workflow and complicate findings aggregation.

### 2. Normalize tool output immediately at the adapter boundary

- **Decision**: Each scanner adapter translates tool-native fields into the core findings schema before results reach reporting or evidence code.
- **Why**: Downstream code should consume one consistent contract regardless of scanner source.
- **Alternative considered**: Preserve raw tool payloads through the pipeline. Rejected because it pushes schema drift into every caller.

### 3. Reuse policy-mode semantics from shared governance work

- **Decision**: The bundle reads advisory/mixed/hard enforcement intent from existing profile and policy mechanisms and only decides which scanners to run plus how to surface failures.
- **Why**: Policy meaning already has a single source of truth in the ecosystem.
- **Alternative considered**: Bundle-local enforcement flags with independent semantics. Rejected because it would drift from policy packs and enterprise governance.

## Risks / Trade-offs

- **Risk**: Third-party scanner version drift could destabilize output normalization. → **Mitigation**: define fixture-based adapter tests and pin expected mappings in spec scenarios.
- **Risk**: A single broad bundle may feel heavy for users who only want one scanner class. → **Mitigation**: keep command flags/profile settings selective while retaining a unified bundle identity.
- **Risk**: Overlap with license/privacy modules could blur product boundaries. → **Mitigation**: document explicit scope lines and keep separate bundles for SPDX and GDPR/PII concerns.

## Migration Plan

1. Land the paired core findings model so adapters target a stable schema.
2. Implement the new package and adapters with fixture-based tests.
3. Add registry entry, docs, signatures, and compatibility range as one release unit.

## Open Questions

- Which dependency-risk backend should be the default on day one: Grype, OSV, or both behind provider switches?
- Should SBOM generation be mandatory for every security run or enabled only when dependency analysis is requested?
