# Design: Repair C14 Installed Payload Layout Handling

## Verified current behavior

Observed on 2026-09-06 (Europe/Berlin): core 0.55.4, official Code Review 0.49.76, Python 3.12.13, Linux x86-64. Strict range review resolved scope but returned UNKNOWN/exit 1; no analyzer completed. Core verify_module_artifact returned true. derive_core_0_55_1_install_handoff caught FileNotFoundError for the absent flat directory while src/specfact_code_review existed.

The public reproduction range is nold-ai/specfact-cli b897976ed994a708a7ad1984839090b2f858e00c to daf05baa9303ef914f5659eafe940146d311af25. The analyzer OCI manifest was sha256:f00ac813f428b7c2ef3d1ce3400496f67ca2d508064e6efc55af1ba6c4697461. Docker namespace and cache setup were controlled separately to reach the defect. No signature checks or module bytes were modified.

## Intended correction

The primary implementation surface is packages/specfact-code-review/src/specfact_code_review/run/toolchain.py: `_installed_payload_manifest` and `_copy_builtin_entry`. The runner's `_official_installed_payload` handoff should preserve a useful failure reason.

Resolve exactly one real package root from the two supported relative prefixes: src/specfact_code_review and specfact_code_review. Reject ambiguity, missing roots, symlinks in relevant directory components, and non-regular payload entries. Retain the authenticated installed root; do not rewrite the installation or import ambient host code.

Manifest paths remain relative to the actual installed root, including src when present. Copying accepts only the validated prefix and strips that prefix into the unchanged /opt/specfact/builtin/specfact_code_review destination. Recheck bytes and modes at copy time. Existing flat candidate staging remains byte/digest compatible.

The existing handoff schema and report shape need no change. Preserve signature, registry, core-install marker, metadata, checksum, provenance, and digest verification. Detailed diagnostics identify layout/handoff failure without treating the signed installation as untrusted merely because its package has a src prefix.

## Verification and risks

Test the real core installer with a signed fixture and actual signature verification, not a mocked True result or a manually flattened fixture. Delete the download archive before deriving the installed handoff and invoking copied built-ins. Cover minimum core 0.55.1 and reproduced core 0.55.4, flat candidate parity, resources, modes, drift, ambiguous roots, and symlinks.

A remaining runtime, project-dependency, or candidate-policy UNKNOWN after repair is independent evidence, not proof the correction failed or validation passed. Record each result separately. Avoid changing historical C14 lock/checkpoint identities.

## Release and recovery

Future implementation requires a Code Review patch version, checksum/signature verification, registry parity, and the canonical post-merge publication workflow. Do not manually sign with unavailable credentials or mutate installed signed modules. Keep core compatibility unchanged unless verification proves a new dependency. If release verification fails, withhold publication and return to implementation evidence; preserve the previous published artifact identity.

This planning PR performs none of those release actions. The issue remains open, and implementation is not complete merely because this proposal lands.
