# Requirements 08: Bounded Red-Green Proof

> **Parked and superseded — do not implement or archive.** Modules issue #414 and
> paired core issue #675 were closed as `not planned` on 2026-08-29. The
> lower-cost seal-bound checkpoint design in modules #431/#434 and core
> #682/#684 supersedes this historical replay approach. The folder remains at
> its governed path but is excluded from implementation; it must not be archived
> because that would merge unimplemented specifications into canonical
> requirements.

This module-side change defines the typed B/R/H/D replay capsule and chronology reconciliation contract consumed by paired core issue nold-ai/specfact-cli#675 and PR #674. Core resolves Git and executes tests; modules validate the versioned capsule and report only the bounded claim.

Planning only: no package behavior, registry artifact, version, or signature changes on this branch.
