# Managed macOS boundary experiments and prerequisites

This directory contains prerequisite checks, fixed-fixture startup and control
brokers, a sealed Semgrep bootstrap and an independent observer. These are not a production backend. Production selection remains disabled. The current acceptance
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
remain mandatory. The fixed-bootstrap creation-to-tracing subset now passes on the physical Mac;
full platform/boundary admission remains mandatory before production integration.
Withholding project execution alone never proves pre-trace cleanup.

## Native startup proof (maintainers)

```sh
hatch run python scripts/macos_managed_boundary/startup.py \
  --repetitions 100 --out .specfact/native-compat/startup-confinement-100.json
```

This compiles and ad-hoc signs fixed ARM64 fixtures using maintainer build tools.
It creates temporary ordinary-user GUI launchd jobs; it installs no LaunchAgent.
LaunchOnlyOnce job removal and independent worker disappearance are checked before
harness cleanup. No arbitrary project code or commands are accepted. The deny-default
fixture policy is not the eventual analyzer/project profile. All receipts retain
production_approved=false and signed_boundary_verified=false, even after 100
repetitions. [Measured results and remaining gates](../../openspec/changes/code-review-native-platform-execution/STARTUP_BOUNDARY_RESULTS.md).

## Native private control and sealed analyzer proof (maintainers)

```sh
hatch run python scripts/macos_managed_boundary/control.py \
  --repetitions 100 --out .specfact/native-compat/control-proof.json
hatch run python scripts/macos_managed_boundary/analyzer.py
```

The control protocol takes bounded fixture operations and broker handles only,
with real peer audit-token and private-capability authentication. The analyzer
command takes no customer input: it verifies the pinned local native core and
seven bundled libraries, then runs four clean/defective fixtures inside tracing
and a separate deny-default profile. It requires the previously prepared local
Semgrep candidate; it does not silently acquire host tools. Approved loader
directory/ancestor metadata and exact dylib grants preserve forbidden host-file,
process, descriptor and network controls. This is two actual analyzer members,
not proof of all ten inside the boundary or the project-manager corpus.
Receipts remain experimental and cannot enable production selection/publication.

## Fixed image handoff acceptance

The control experiment now verifies the signed replacement's dynamic code identity
at the kernel-owned exec stop, before target initializers. Its v2 receipt includes
four signed artifacts, shared probes and SDK/MIG inputs. It tests genuine traps,
failed/second exec, corrupt and validly signed wrong targets, inherited confinement,
and cancellation/connection loss/broker death both at the held replacement stop
and after entry. All 19 lifecycle cases require 100 repetitions plus 25 protocol
checks. Initial-distribution signing and false production flags remain unchanged.
This is a fixed C target, not the production interpreter or all-ten-analyzer runtime.
