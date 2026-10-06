# Native capsule build, staging and installation

Status on 6 October 2026 (Europe/Berlin): implementation is reviewable in draft
PR [#498](https://github.com/nold-ai/specfact-cli-modules/pull/498). Local actual
ARM64 capsule execution works. Protected hosted acceptance, publisher signing,
public distribution and independent ordinary installation remain acceptance
gates. No Apple Developer account is required for this staged delivery.

## Implemented delivery path

`.github/workflows/native-capsule-release.yml` builds managed uv/Git and three
hash-pinned, offline dependency closures in secret-free macOS jobs. CPython
cp311/cp312/cp313 archives contain the actual ten analyzers. Transport preserves
archive bytes; the separate managed input executables have their fixed modes
restored after Actions artifact transport. `scripts/native_release/build.py`
reuses the existing reproducible component, analyzer and unsigned archive builders.

Nine native execution jobs use these exact archives on macOS 14, 15 and 26. They
check the narrow loader profile, actual extraction/codesign, all ten analyzers,
real Flask tests/coverage, a loaded MarkupSafe native extension and offline reuse.
The existing fixed startup/control suites remain independently required. An
additional delivered-component harness uses the final broker/bootstrap/verifier/
self-test/policy bytes, without rebuilding or re-signing, for 100 runs each of
controller loss, failed bootstrap and exception-port denial. The five-second
cleanup budget starts before controller termination and includes process
observation time. Supported image drift fails; local newer-Mac results never
stand in for a supported matrix receipt.

The protected Linux signer treats artifacts as data. Before loading a private
key it validates source/workflow identity, the complete nine-cell matrix,
canonical bounded JSON, exact ABI/source/manifest/archive identities, strict
USTAR structure, all member digests, final native signing metadata and the exact
loader entitlement policy. Only CPython and Semgrep may have
`com.apple.security.cs.disable-library-validation=true`; every other image must
have empty entitlements. Integer `1` cannot satisfy the boolean rule. The signer
never extracts or executes candidate payloads. It signs the existing manifest
bytes against the tracked public root and writes three signed archives plus a
module-resource/catalog overlay to a fresh, exclusively created staging directory.
The staging receipt remains `production_eligible=false`.

The optional candidate uploader verifies the signed staging inputs against the
same external public root, pushes plain archive blobs through ORAS, and verifies
the catalog's digest/size through the existing anonymous GHCR reader. No signing
key reaches the uploader. A private or missing blob fails anonymous verification.
Candidate upload requires an explicit workflow input and a separate protected
publication approval; it is disabled by default. Upload alone does not promote
catalogs or establish production acceptance.

`.github/workflows/native-capsule-customer.yml` independently installs public
`specfact-cli==0.55.4` and the official signed marketplace module into a fresh
ordinary-user HOME/venv. It verifies installation, forbids developer overrides
and registry credentials, and invokes the normal installed CLI. The nine-cell
customer matrix must complete anonymous cold acquisition, actual ten-analyzer
execution, project tests/coverage/extensions, offline project preparation and
identical offline capsule compositions. It records real quarantine attributes
read-only. An unattended CLI cannot confirm a visible first-run trust dialog;
that limitation is recorded explicitly rather than claiming a warning appeared.

## Protection and human promotion

Before enabling authority, maintainers must configure GitHub environments
`native-capsule-signing` and `native-capsule-publication` with protected-branch
restriction, required independent reviewers, self-review prevention and admin
bypass disabled. Signing additionally requires the dedicated environment-scoped
`SPECFACT_NATIVE_CAPSULE_PRIVATE_SIGN_KEY` and optional passphrase; do not use
repository-scoped publisher secrets. The workflow reads the actual environment
protection configuration before its authority step and rejects missing or
weaker protection. These environments were not created or populated locally.

1. Review and merge the implementation through dev to protected main; require
   exact-head Linux review and the secret-free native matrix. Dispatch the main
   workflow with candidate upload disabled; all nine archive receipts must pass.
2. After independent signing approval, inspect the signed staging artifact:
   exact manifests/signatures/public root, archive SHA-256/size, catalog resources
   and source receipt. Approve candidate upload only when publication is intended.
   Configure the capsule GHCR package for anonymous public pulls. The separate
   publication environment approval is still required.
3. Submit the generated module-resource/catalog overlay in a reviewed change.
   Bump the affected module version, synchronize the registry and use CI-only
   module signing. No local publisher key is needed or authorized. Publish the
   reviewed signed module through the existing release process after approval.
4. Run the independent installed-customer matrix and repeat canonical fresh
   installation on an independent supported Mac/VM. Record actual trust behavior
   and findings. Close #460 and archive the OpenSpec change only after all required
   native, manager, physical-project and Linux acceptance is complete.

The manifest signature uses the project's publisher trust root, which is
separate from Apple's application identity. Ad-hoc native signatures and normal
initial trust warnings are owner-approved at this stage. Do not strip quarantine,
change global trust settings, disable Gatekeeper or expand entitlements to force
an acceptance result. Apple Developer ID signing/notarization can follow later.

## Local reproducible demonstration

A real cp312 archive was rebuilt through the new public build entry point at
`/private/tmp/specfact460-release-cli-cp312/darwin-arm64-cp312`. Its archive SHA-256
is `618c80b1219d3307cd9d030f255a7fd682e748f3bc9412bb698a6fe3bb5ae2da` (612231680 bytes),
and manifest SHA-256 is
`a087b5bf74b0b5a60f2bee1cdf046c670929be6ab995260c73e72b758a7b8e5a`.
It is byte-identical to the preceding actual candidate archive.

From this attached worktree, with its verified Hatch environment, a new local
candidate demonstration can be run with a fresh output directory:

```sh
SOURCE_SHA="$(git rev-parse HEAD)" \
PYTHONPATH="$PWD/packages/specfact-code-review/src:$PWD" \
  hatch run python -m scripts.native_release.acceptance --mode candidate \
  --artifact /private/tmp/specfact460-release-cli-cp312/darwin-arm64-cp312 \
  --work /private/tmp/specfact460-my-native-demo --runner local
```

This downloads the pinned Flask project, performs actual cold/offline preparation
and launches the capsule. It creates an ephemeral fixture manifest key to
exercise authentication, extraction and real codesign, then injects only the
candidate lease into the real module command. It is deliberately **candidate
evidence**, not a public-key-authorized installation. No publisher private key
is accessed. A fresh directory is required; failed or existing output is retained
for diagnosis. Project findings remain genuine PASS/FAIL outcomes rather than
being suppressed to make the demonstration green.

Observed proof: `/private/tmp/specfact460-release-acceptance-cp312-v4/review.json`
contains all ten completed analyzer rows, 20 collected tests/20 actual call
records and 162 coverage files. The added actual MarkupSafe native-extension
test passes. Cold and offline project identities agree; actual capsule cache
verification passes. Overall assurance status is PASS. Scope and local
receipt retain `customer_installation=false`, `production_eligible=false` and
`native_boundary=false` because this Mac is 27.0.1/26A434 rather than a supported
matrix image. After the deadline correction, exact delivered-component proof
passed again at
`/private/tmp/specfact460-release-delivered-boundary-cp312-v3/delivered-boundary.json`.

## Limits, operating cost and recovery

Hosted runner image or authenticated dependency drift fails closed: maintainers
must inspect and review any new pins rather than widening validation. Missing
protected environment/key/public GHCR access prevents staging/distribution;
local working capsule proof does not bypass those gates. Ad-hoc trust behavior
may require user acknowledgement or block execution on a managed Mac; record the
actual outcome and keep integrity and boundary checks enforced.

One fresh run builds managed tools and three approximately 600 MB archives,
then uses nine parallel native acceptance cells; hosted build jobs allow up to
60 minutes, execution up to 60 minutes per cell and customer checks up to 90
minutes. These are job ceilings, not measured completion estimates. Artifacts
are retained for seven days; preserve reviewed release evidence before expiry.
Published candidate blobs may remain in GHCR even after a partial upload fails.
Recovery is to withhold the catalog/module promotion or withdraw/supersede its
reviewed entries; immutable blob identities and prior evidence remain intact.
Linux catalog entries and released module payloads are unchanged by this tooling.

Primary workflow references (accessed 6 October 2026):
[GitHub environment protection](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments),
[deployment review](https://docs.github.com/en/actions/how-tos/managing-workflow-runs-and-deployments/managing-deployments/reviewing-deployments),
[ORAS push/pull](https://oras.land/docs/how_to_guides/pushing_and_pulling/).
