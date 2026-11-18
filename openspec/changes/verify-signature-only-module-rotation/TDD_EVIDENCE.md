# Signature-only source manifest verification

The before run rejected a same-version source manifest with a valid replacement signature. The seven negative cases passed.

The after run passed 61 focused verifier, resource integrity, and workflow tests on Python 3.11. The new cases verify admission with the pinned replacement key and denial for an alternate key, a substituted PEM, a changed checksum, an additional package file, dirty manifest bytes, metadata-only verification, and an immutable cutoff version.

Tests used disposable Ed25519 keys and scratch Git repositories. Existing archives, manifests, and cutoff data remained byte-identical.

## Capsule controllers

The released CLI rejected the rotated source with its bundled legacy key. The two workflow tests failed before the trust bindings were applied.

The released CLI verified the unchanged source with the replacement key. The independent controller passed the exact base-to-head signature handover and verified a signed base without consulting the candidate. Its isolated command returned structured no-impact evidence for a fixture with no changed files. The retired key failed verification. Local capsule, signature, publishing-fixture, docs, and workflow tests passed.
