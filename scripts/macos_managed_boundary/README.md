# Managed macOS boundary prerequisites

This directory contains prerequisite checks, not a broker implementation or
boundary proof. Production selection remains disabled. The current acceptance
contract is [native delivery](../../openspec/changes/code-review-native-platform-execution/design.md).

## Initial distribution (default)

```sh
python scripts/macos_managed_boundary/preflight.py
```

On native ARM64 macOS this checks availability of the system code-signing tool
without accessing the keychain or a notary service. Exit 0 and
`initial_prerequisites_available` mean only these prerequisites are present.
`signed_boundary_verified` and `production_approved` always remain false.
This result verifies no artifact, signature, hardened-runtime behavior or sandbox.
A corrupt payload, invalid native signature or missing boundary proof must still
fail the eventual admission gate.

The intended initial distribution uses build-time ad-hoc native signatures,
verified upstream signatures where applicable and SpecFact-signed manifests
covering final payload bytes. Hardened-runtime settings and narrow reviewed
entitlements must be tested with tracing and confinement. Developers require no
Apple account, local re-signing, compiler or Xcode. Paid Apple credentials and
notarization do not block initial implementation, shipment or canonical GHCR
publication. The actual independent-Mac CLI/GHCR route must pass with default
protections; do not strip quarantine, disable Gatekeeper or require security
overrides to satisfy acceptance.

## Optional Apple follow-up

[#488](https://github.com/nold-ai/specfact-cli-modules/issues/488) /
[`code-review-macos-developer-id-distribution`](../../openspec/changes/code-review-macos-developer-id-distribution/proposal.md)
is blocked by #460 and remains optional and unscheduled. Its explicit check is:

```sh
python scripts/macos_managed_boundary/preflight.py \
  --signing-mode developer-id \
  --identity '<Developer ID Application certificate SHA-1>' \
  --team '<Apple Developer Team ID>' \
  --notary-profile '<existing notarytool keychain profile>'
```

Only public certificate identifiers and a keychain profile name are accepted;
never supply private keys or passwords. Apple credential arguments require the
explicit mode. This retains the fail-closed certificate/team validation and
bounded read-only `notarytool history` probe. Exit 2 means this optional check is
blocked; it cannot block initial delivery. Exit 0 / `credentials_available`
proves neither private-key access, team association nor artifact acceptance.

Developer ID signing, notarization and applicable stapling require protected
maintainer credentials and fresh exact-artifact boundary/loading/installation
acceptance. Customers need none of those credentials. Successful initial ad-hoc
acceptance does not approve differently signed bytes.

## Evidence limits

Unit tests use synthetic command results and prove routing and rejection behavior
only. No caller-supplied receipt grants production eligibility. Independent
five-second survivor checks and 100 repetitions of each startup/lifecycle race
remain mandatory. The creation-to-tracing ownership gap must be resolved before
analyzer integration; withholding project execution does not prove cleanup of an
untraced bootstrap after broker death.
