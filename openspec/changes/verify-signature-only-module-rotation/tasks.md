## 1. Version check

- [x] Reproduce rejection of a valid signature-only rotation.
- [x] Verify that the unchanged payload passes and mixed changes still require a version bump.
- [x] Confirm the signing environment remains protected and the publisher remains paused.

## 2. Authenticate capsule review controllers

- [x] 2.1 Reproduce the released CLI rejecting the rotated source signature.
- [x] 2.2 Bind candidate and independent review controllers to the pinned replacement key.
- [ ] 2.3 Run capsule and review checks with the frozen cutoff and publisher pause intact.

## 3. Close legacy signing paths

- [x] 3.1 Reproduce the missing-key failure on the push step with an empty legacy secret.
- [x] 3.2 Keep push and PR verification read-only and remove the legacy source-manifest writers.
- [x] 3.3 Test replacement-signature reproduction and exact cutoff verification with disposable keys.
