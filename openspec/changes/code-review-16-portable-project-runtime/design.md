# Design: portable project runtime

## Interface and data flow

Keep existing review invocations. Add `specfact code review runtime inspect --json`, `runtime prepare --json`, `run --project-config PATH`, and `run --project-runtime PATH`. Inspect is read-only. Prepare is also invoked automatically for dependency-sensitive analysis.

A package-manager-neutral project plan records manager/environment, Python constraints, dependency and configuration input hashes, selected extras/groups, source roots, pytest policy and declared native libraries. Explicit project configuration wins; verified active context precedes unambiguous repository discovery. Conflicts fail with one actionable diagnostic. Build backend declarations alone do not identify environment managers. Adapters preserve manager semantics and never merge every optional environment.

Prepare in a disposable writable copy using a namespace-isolated builder and a verified capsule interpreter. Separate network dependency acquisition from offline analysis. Do not expose publisher credentials or import project code in the controller. Record manager versions, exact installed distributions, payload and input digests. Cache artifacts outside the source checkout, verify warm reuse, reject symlink/path escape and partially published artifacts. Preserve original manifests, locks and environment files. Native imports report missing shared libraries explicitly.

The v2 descriptor supports local artifacts and binds inputs, platform/ABI and worker identities. It is local build provenance, never an invented publisher attestation. Retain the v1 reader unchanged. Dependency changes across base/head require independent preparations. Dirty/index sources bind their own content, not just HEAD. The host supervisor remains sealed; project dependencies and plugins execute only in disposable target workers. Ordinary package names are allowed in those workers but cannot shadow control entry points. Genuine tool/project constraints conflicts produce UNKNOWN, not changed project pins.

## Pytest and report semantics

Honor configuration precedence, plugin activation, import mode and source roots. Observe actual collection and execution; preserve selected policy and do not suppress controls silently. Unsupported options name the precise reason. Preparation failures retain independent static evidence and produce one root diagnostic referenced by dependent analyzer members. Genuine missing imports after successful preparation remain findings. Local v2 evidence is not eligible for protected pr_range promotion; the existing v1 trust path is unchanged.

## Validation and delivery

Freeze Requests, Hatch, Flask and Poetry commits from the accepted plan. Run real source/test slices under pip/Hatch/uv/Poetry on non-root Ubuntu 24.04 for CPython 3.11/3.12/3.13. Include a labelled reconstruction of #472, cold/offline-warm paths, ordinary GITHUB_ACTIONS, changed lock, corruption, native imports and controlled defects. Required applicable analyzer completion is independent of zero findings. The signed public release repeats the candidate matrix. Keep #472 open pending original customer reproduction.

Run all canonical quality/signature/review/Requirements gates and fix PR findings. Limit corpus jobs to 90 minutes and record actual seconds/bytes. Roll back through reviewed revert and new signed publication; never mutate immutable published payloads. Archive only through openspec after merge and acceptance.

Private VCS context is an explicit object export, not a repository clone. The selected commit, captured index tree, recorded tags and shallow boundary define its object closure. Git plumbing transfers only that closure into fresh metadata; unrelated refs, reflogs, unreachable objects, alternates and source-local configuration are not imported. This preserves SCM version inputs while binding cache reuse to the Git state build hooks can observe.

Target startup installs analyzer-owned import resolution before project paths are processed by site initialization. Verified analyzer origins and namespace search locations must stay under the member installation. This governs ordinary import resolution and detects unexpected preloads; it does not claim that a Python import finder sandboxes arbitrary project code within the same interpreter. Project code remains confined to the isolated target worker, and project-owned graph dependencies retain their selected versions.
