# Resolve native Hatch PR review findings

## Why

The owner requested merge readiness for PR #524 while retaining the native-only direction, signing and independent security. Two open review findings identify missing directory-symlink bindings in project provenance and a migration baseline that disappears after squash merge. The exact-head candidate also reports complexity regressions in native test functions.

## What changes

- Fingerprint nonignored directory-symlink bindings so in-project retargeting cannot preserve stale provenance.
- Keep the reviewed migration baseline as committed path, Git mode and blob identities, independent of feature-branch history retention.
- Preserve deletion allowance, addition/edit rejection, policy fingerprint binding and safe explicit historical comparisons.
- Decompose the affected native tests without changing assertions or acceptance.

## Scope and limits

This is a correction to the first existing/cold detached Hatch milestone and its native migration guard. It does not introduce alias traversal, new admission restrictions, capsule repairs, ordinary reviewer cutover, another manager, publication or security-test ownership transfer. Existing project traversal exclusions remain effective; binding fingerprints do not claim complete content closure for external or ignored alias targets. Native local and Linux acceptance remain separate from independent protected review.

The remaining capsule failures and independent timeout remain blocking. Merge readiness cannot be claimed until all applicable requirements pass. No merge or archive is authorized.
