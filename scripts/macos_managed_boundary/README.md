# Managed macOS boundary milestone

This directory currently contains **maintainer prerequisite checks only**. It is
not a runtime, broker implementation, signed boundary proof or customer setup
procedure. Production selection remains disabled. The approved contract and
acceptance tasks live in
[`code-review-native-platform-execution`](../../openspec/changes/code-review-native-platform-execution/design.md).

## Check release-signing prerequisites

On an ARM64 Mac configured for maintainer builds:

```sh
python scripts/macos_managed_boundary/preflight.py \
  --identity '<Developer ID Application certificate SHA-1>' \
  --team '<Apple Developer Team ID>' \
  --notary-profile '<existing notarytool keychain profile>'
```

Only public certificate identifiers and a keychain profile name are accepted;
never supply private keys, certificate passwords or Apple credentials in these
arguments. Maintainers configure their signing key and notarization profile
through their approved credential-management process. Customers need none of
these credentials, a compiler, Xcode, or this script.

The preflight reads valid signing identities and authenticates a read-only
`notarytool history` request. It prints a redacted JSON prerequisite receipt and
exits 2 when blocked. It does not compile, sign, submit, download or execute a
candidate. Exit 0 means only that these credential probes succeeded. A successful
probe does not prove private-key signing access, team association of the notary
profile, entitlement acceptance, artifact notarization, or runtime compatibility.
Those checks belong to the actual signed artifact pipeline.

Before any acceptance run, that pipeline must sign the broker/bootstrap with
Developer ID and hardened runtime, verify exact identity and entitlements, obtain
and validate notarization for the final bundle, and bind observer results to its
final digest and OS build. No receipt supplied by a caller can waive those steps.
No ad-hoc fallback is provided here.

## Evidence limits

Unit tests use synthetic command results and exercise rejection paths, including
missing/ad-hoc identities, wrong certificate class/team, notary failures and
malformed responses. They do not run a worker or prove tracing/confinement. The
independent five-second survivor checks and 100 repetitions of each startup and
lifecycle race remain mandatory before production integration.

The creation-to-tracing interval is a separate design obligation: withholding
untrusted execution is not proof that an untraced bootstrap disappears after
broker death. Do not proceed to analyzer integration while ownership during that
interval is unresolved.
