## Context

Privacy and GDPR governance need specialized detection, redaction, and region-aware policy handling that would be unwieldy inside a general security bundle. This change defines the modules-side package that runs privacy-focused detectors, evaluates EU/GDPR rule packs, and emits safe normalized findings through the paired core contracts.

## Goals / Non-Goals

**Goals:**

- Define the package structure and command ownership for `specfact-pii-gdpr`.
- Normalize PII/GDPR detections into the paired core findings model.
- Ensure evidence and reports stay safe to store by supporting redaction-aware output handling.
- Keep GDPR/EU rule selection aligned with shared policy-pack semantics and the paired core baseline.

**Non-Goals:**

- Replace the broader security bundle for SAST, SCA, SBOM, or secrets.
- Implement enterprise server-side policy management in the bundle.
- Guarantee legal sufficiency outside the scope of the explicitly codified rule packs.

## Decisions

### 1. Ship privacy/GDPR checks as a dedicated bundle

- **Decision**: Create `packages/specfact-pii-gdpr/` with its own manifest and `privacy` command.
- **Why**: Privacy review needs different detectors, output-handling constraints, and ownership expectations than generic security scanning.
- **Alternative considered**: Fold privacy into `specfact-security`. Rejected because it would mix redaction-sensitive workflows into a broader operational surface.

### 2. Make redaction a first-class adapter responsibility

- **Decision**: Detector adapters return normalized findings plus redaction-safe evidence references, not raw PII payloads.
- **Why**: The modules repo must not create a privacy tool that leaks the very data it flags.
- **Alternative considered**: Preserve raw samples for debugging. Rejected because it conflicts with the GDPR/minimization posture described in the plan.

### 3. Bind EU/GDPR behavior to shared rule packs

- **Decision**: GDPR articles, lawful-basis checks, and region/residency assertions come from the paired core baseline plus shared policy-pack selection, not bundle-local hard-coded mode flags.
- **Why**: Privacy governance needs one source of truth for what counts as compliant.
- **Alternative considered**: Bundle-local configuration only. Rejected because it would drift from core policy semantics and enterprise extensions.

## Risks / Trade-offs

- **Risk**: Detector precision may vary across languages and file formats. → **Mitigation**: specify deterministic fixtures and safe false-positive handling in tests.
- **Risk**: Over-redaction may reduce remediation usefulness. → **Mitigation**: preserve structured evidence references and field/type classifications while suppressing raw values.
- **Risk**: Users may misread the bundle as a full legal compliance product. → **Mitigation**: document explicit boundaries and keep requirements tied to codified rule packs.

## Migration Plan

1. Confirm the paired core privacy/GDPR contracts are stable enough for integration.
2. Implement the new package, detector adapters, and redaction-safe reporting flow.
3. Add docs, registry metadata, signatures, and compatibility ranges together for release.

## Open Questions

- Which detector backend gives the best default balance between offline operation and acceptable false-positive rates?
- Should residency checks operate only on explicit configuration/metadata inputs in the first release, or also inspect provider defaults?
