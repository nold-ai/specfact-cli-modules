# OpenSpec Integration Contract

This modules-side contract must be read with the core repository's
`openspec/INTEGRATION.md`. It records ownership boundaries for active paired
changes without creating runtime behavior.

## Preflight Ownership

- Core `preflight-01-design-contract-core` owns design-contract,
  role-classified scope, component/risk/verification intent, Requirements-plan
  references, validation-result, digest, approval-seal, and side-effect-free
  verifier interfaces.
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
  packaging after the signed #434 handoff. That handoff is one exact signed
  module identity plus separately named preflight and implementation-check
  workflow identities/digests. Adapters map native invocation and assets only.
- Core `preflight-05-implementation-conformance` owns worktree/index/range
  snapshot, obligation-map, finding/result, authority, and pure comparison
  interfaces. Paired modules owns checkpoint/conform commands, C14-backed Git
  extraction, Requirements pytest/JUnit and code-review evidence, caching,
  pre-commit policy, remediation packets, bounded agent workflow,
  checkpoint/conformance-result rendering, optional atomic snapshot/result
  persistence under its distinct result schema, signing, and publication of the
  module identity plus separately bound preflight and implementation-check
  workflow identities/digests. These surfaces are separate from
  `preflight-02-assurance-runtime`, which exclusively owns preflight
  readiness/validation/seal rendering and persistence.

## Shared Rules

- Architecture-01, governance-01, traceability, and native OpenSpec/Spec Kit
  import remain upstream inputs; preflight must not redefine their payloads.
- The signed module skill is the canonical workflow source. General AGENTS.md,
  OpenSpec, Spec Kit, ECC, hatch3r, and Codex instructions contain a compact
  gate/reference only.
- Python validators are the canonical determinate checks. Prompts and adapters
  must not recompute readiness, approval, checkpoint, or conformance status.
- A seal proves exact reviewed-input identity and recorded approval, not design,
  LLM, implementation, security, or semantic correctness.
- Any pre-implementation bound-input change invalidates readiness and requires
  a complete rerun and explicit user approval. During later conformance, the
  approved seal is verified against its sealed contract and base source
  snapshot while worktree/index/range implementation evidence is captured as a
  separate identity; implementation commits do not silently rewrite the seal.
- Worktree/index checkpoint results have local authority only. They cannot be
  promoted to protected PR-range evidence; final conformance requires a new
  explicit immutable base/head evaluation.
- Native GitHub parents, project status, blockers, and blocked-by relationships
  are required before implementation; body-only references are insufficient.

## Delivery Sequence

`core #682 -> modules #431 -> core C14 #680/#683 -> modules #432 -> core #684 -> modules #434 -> core #251 -> core #253 -> modules #433`.
Modules C15 `#417` -> core C15 #679 remains an independent signal-calibration
branch after stable #432. Existing policy/exception blockers remain in force.
