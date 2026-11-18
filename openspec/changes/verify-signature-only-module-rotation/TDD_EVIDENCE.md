# Signature-only source manifest verification

The before run rejected a same-version source manifest with a valid replacement signature. The seven negative cases passed.

The after run passed 61 focused verifier, resource integrity, and workflow tests on Python 3.11. The new cases verify admission with the pinned replacement key and denial for an alternate key, a substituted PEM, a changed checksum, an additional package file, dirty manifest bytes, metadata-only verification, and an immutable cutoff version.

Tests used disposable Ed25519 keys and scratch Git repositories. Existing archives, manifests, and cutoff data remained byte-identical.

## Capsule controllers

The released CLI rejected the rotated source with its bundled legacy key. The two workflow tests failed before the trust bindings were applied.

The released CLI verified the unchanged source with the replacement key. The independent controller passed the exact base-to-head signature handover and verified a signed base without consulting the candidate. Its isolated command returned structured no-impact evidence for a fixture with no changed files. The retired key failed verification. Local capsule, signature, publishing-fixture, docs, and workflow tests passed.

The next hosted run prepared both index descriptors with the replacement key. Independent preparation still failed when the authenticated source view lacked an installer receipt. A local replay returned `official_installed_module_missing` for that source view. The released installer then produced a valid receipt for the byte-pinned historical reviewer and its three frozen dependencies from an isolated file registry. The review fixture uses the same historical archive and no mutable registry lookup.

The hosted candidate analysis also failed to run shell-dependent tests. A local probe without Bash reproduced the missing executable. The signed runtime supports Git, sed, and uname as additional host tools.

## Public verification and protected reproducibility

The original push step exited 1 with `Missing SPECFACT_MODULE_PRIVATE_SIGN_KEY` when the legacy secret was empty. Three regression tests also failed on the write-enabled verification job, legacy manual signer, and approval signer.

The independent review caught a mismatch between the manifest bytes and the full payload signed by `sign-modules.py`. A fixture signed by the production signer reproduced the failure. The corrected job uses the verifier's full filesystem payload and reproduces the signature without writing a new manifest.

The exact public verification step passed on the push, PR, and manual verification paths with no signing secrets. Each verified seven manifests and enforced version checks against `dev`. On Python 3.12, 28 focused verifier and workflow tests passed. The signing fixture uses disposable keys and checks that wrong keys, changed cutoff trees, and changed signatures fail. Actionlint, Ruff, and strict OpenSpec validation passed.
