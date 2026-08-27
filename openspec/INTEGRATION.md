# OpenSpec Integration Contract

This modules-side contract must be read with the core repository's
`openspec/INTEGRATION.md`. It records ownership boundaries for active paired
changes without creating runtime behavior.

## Preflight Ownership

- Core `preflight-01-design-contract-core` owns design-contract,
  validation-result, digest, approval-seal, and side-effect-free verifier
  interfaces.
- Modules `preflight-02-assurance-runtime` owns executable Python validators,
  CLI orchestration, rendering, explicit persistence, and canonical bundled
  `specfact-preflight` workflow content.
- Core `preflight-03-dogfood-hardening-and-release` owns C14 dogfood evidence
  and the bounded go/no-go decision. The paired modules change owns only
  evidence-backed hardening, compatibility proof, signing, and publication.
- Core `ai-integration-01-agent-skill` owns generic discovery/installation and
  canonical `.agents/skills` export. Core `ai-integration-03-instruction-files`
  owns generated gate references. Neither owns the workflow body or validators.
- Modules `preflight-04-harness-adapters` owns thin Codex, ECC, and hatch3r
  packaging. Adapters map native invocation and assets only.
- Core `preflight-05-implementation-conformance` owns later comparison
  interfaces; paired modules owns extraction and runtime comparison. This phase
  is explicitly excluded from the preflight MVP.

## Shared Rules

- Architecture-01, governance-01, traceability, and native OpenSpec/Spec Kit
  import remain upstream inputs; preflight must not redefine their payloads.
- The signed module skill is the canonical workflow source. General AGENTS.md,
  OpenSpec, Spec Kit, ECC, hatch3r, and Codex instructions contain a compact
  gate/reference only.
- Python validators are the canonical determinate checks. Prompts and adapters
  must not recompute readiness, approval, or conformance.
- A seal proves exact reviewed-input identity and recorded approval, not design,
  LLM, implementation, security, or semantic correctness.
- Any pre-implementation bound-input change invalidates readiness and requires
  a complete rerun and explicit user approval. During later conformance, the
  approved seal is verified against its sealed contract and base source
  snapshot while the implementation head/range is captured as a separate,
  explicit identity; implementation commits do not silently rewrite the seal.
- Native GitHub parents, project status, blockers, and blocked-by relationships
  are required before implementation; body-only references are insufficient.

## Delivery Sequence

`core #682 -> modules #431 -> core C14 #680 -> core #683 -> modules #432`.
After the signed release, `#251 -> #253 -> modules #433`; both modules #433 and
core #684 block modules #434. Issue #434 remains a later branch; modules C15
#417 -> core C15 #679 remains the signal-calibration branch. Existing
policy/exception blockers remain in force.
