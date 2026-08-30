## Context

This is the first release-authorized phase. It begins only after the paired core dogfood change produces a go decision and an evidence-backed hardening ledger. The change closes the gap between an unpublished working prototype and a stable, signed module contract that downstream installers and C15 can trust.

## Goals / Non-Goals

**Goals:**

- Convert accepted dogfood observations into generalized regression cases and minimal fixes.
- Prove the final module against an immutable compatible core identity and official install/load path.
- Publish one signed stable module containing the runtime and canonical workflow assets.
- Hand exact published identities to downstream skill installation, instructions, conformance, and C15 work.

**Non-Goals:**

- Add speculative validators or redesign the core contract without separate accepted scope.
- Publish external harness adapters.
- Claim general correctness or implementation conformance.

## Decisions

### 1. Evidence ledger gates scope

Every implementation task must cite the paired core dogfood observation, affected contract path, generalized rule, regression test, and owning component. Items without that chain are excluded or filed separately.

### 2. Hardening reruns the same loop

After each accepted fix, the same C14 dogfood corpus and all declared regression cases rerun. A fix that changes contract semantics invalidates prior approval and requires a core contract change plus new dogfood approval.

### 3. Release surfaces move together

Module source, canonical workflow assets, package manifest, version, core compatibility, registry metadata, structured release-history entry, checksums, signatures, and publication evidence are one atomic release scope. Publication cannot pass unless the new version has its canonical history entry. The change follows the repository's signing and version-bump gates and does not hand-author publication artifacts outside the official scripts/workflows.

### 4. Compatibility is proven, not inferred

The release advertises only a core version identity exercised through a fresh official install/load and full contract/CLI/workflow regression matrix. A broad future-version range is not inferred from one lower-bound smoke. The publication pre-check must reject empty compatibility metadata or a claimed identity/range that has no matching immutable matrix evidence before signing or registry publication.

### 5. Stable workflow remains canonical

The released module contains the canonical `specfact-preflight` workflow and its version/digest identity. The official installer or preflight check verifies the signed workflow identity and its delegated CLI identity as one release-bound tuple. Core #251 installs/exports that verified asset; core #253 references it from generated instructions; preflight-04 packages thin external adapters. None may fork validator logic.

### 6. Publication is reversible

Publication is blocked until the selected registry and installer expose a supported withdrawal or supersession operation and a tested installer-rejection path for the withdrawn identity. The hardening ledger must name the exact official registry command or workflow and released core installer contract that enforce this path; the current latest-entry/checksum flow alone is not treated as revocation. If no such released interface exists when implementation begins, modules work stops for a separately accepted core change. If post-publication verification fails, the supported operation marks the faulty identity unavailable, the installer rejects it before download or installation, and downstream adoption remains blocked. A prior verified version stays authoritative when one exists; after failure of the first stable publication, no preflight identity remains installable until a new release is verified.

## Risks / Trade-offs

- **Overfitting to C14:** Require generalized rules plus a bounded independent regression corpus.
- **Compatibility overclaim:** Pin only tested identities and retain explicit matrix evidence.
- **Signed asset drift:** Run filesystem-payload signature verification with version-bump enforcement before publication.
- **Downstream race:** Publish immutable handoff identities before unblocking core #684 or C15. Modules #434 consumes this handoff plus core #684 before #251/#253/#433 can proceed.

## Migration and Rollback

The first stable release is opt-in. Users of the unpublished dogfood build migrate by reinstalling the signed stable module and regenerating local workflow exports through the supported installer. Before publication, candidate-written persisted state must have a tested backward-read path, migration with backup/restore, or explicit no-install/reset outcome when the last verified module cannot read its schema. When no prior stable preflight baseline exists, publication remains blocked until that first-release outcome is proven. Rollback uses the proven registry operation to make the faulty identity unavailable and restores a prior verified module identity as authoritative when one exists; otherwise it leaves no preflight release installable. Neither outcome claims that an unsupported persisted schema is readable.

## Open Questions Deferred to Implementation

- Exact stable version based on the repository state when hardening begins.
- Whether dogfood exposes a need for a schema migration tool; it is not assumed in this proposal.
