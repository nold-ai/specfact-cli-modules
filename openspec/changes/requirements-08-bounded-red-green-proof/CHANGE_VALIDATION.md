# Change Validation

## Status

`PARKED / SUPERSEDED — DO NOT IMPLEMENT OR ARCHIVE`

Issues #414 and nold-ai/specfact-cli#675 are closed as `not planned`. The
seal-bound development assurance work in #431/#434 and core #682/#684 replaces
the expensive historical replay proposal. No package behavior or signed release
implements this change, and archiving it would incorrectly merge unimplemented
requirements into the canonical specification.

## Planning evidence

- Paired core issue/PR: nold-ai/specfact-cli#675 / nold-ai/specfact-cli#674.
- Modules tracking issue: #414 with required labels and assignee.
- Strict command required before implementation: `openspec validate requirements-08-bounded-red-green-proof --strict`.
- Failing-before and passing-after implementation artifacts: unavailable; no behavior changed.
- Package, registry, archive, checksum, signature, and verifier-epoch evidence: unavailable until implementation and release.

## Supersession record

- Modules issue #414: closed `not planned` on 2026-08-29.
- Core issue #675: closed `not planned` on 2026-08-29.
- Replacement planning: modules #431/#434 and core #682/#684.
- The folder remains at its governed `openspec/changes/` path because repository
  rules prohibit a manual move or rename. It is parked by explicit status and
  roadmap exclusion, not by filesystem relocation.
- Un-parking requires fresh evidence, an explicit roadmap decision, and strict
  revalidation. Do not use `openspec archive` unless the behavior is first
  implemented, verified, shipped, merged, and its canonical specification
  promotion is explicitly approved.
