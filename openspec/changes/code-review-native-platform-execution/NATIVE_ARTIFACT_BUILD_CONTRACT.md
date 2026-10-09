# Native capsule artifact build contract

## Scope

This contract covers the maintainer-side conversion of an already complete and
verified Darwin ARM64 runtime root into a bounded native capsule candidate. The
builder does not resolve dependencies, download tools, compile code, or admit a
runtime. Customer execution never invokes this builder.

## Inputs and trust

- The runtime root SHALL contain the broker, bootstrap, selected CPython ABI,
  every analyzer/tool, policies/adapters, provenance, and license files.
- A caller-supplied closure SHALL partition every input file exactly once.
  Undeclared files, missing members, symlinks, non-regular files, alias-prone
  paths, and case-insensitive path collisions SHALL fail the build.
- The generated `native-signing-v1` closure identity is reserved. An input
  component with that identity SHALL fail rather than lose its members when
  signing metadata is added.
- Provenance and license components SHALL be present and non-empty. Their bytes
  remain ordinary signed payload members.
- The environment SHALL be one of `darwin-arm64-cp311`,
  `darwin-arm64-cp312`, or `darwin-arm64-cp313`. Backend and policy identities
  SHALL be explicit bounded identifiers.

## Native closure and signing

- Every native image SHALL be Mach-O with an exact generic ARM64 slice. Mixed
  ELF/Mach-O roots, x86-only or arm64e-only images, unsafe absolute paths,
  Homebrew load paths, escaping or unresolved rpaths, missing dylibs, and
  malformed load commands SHALL fail through the shared native inventory.
- Every Mach-O SHALL be emitted owner-executable and every other payload member
  owner-read-only. An input executable that is not Mach-O SHALL fail.
- Every Mach-O SHALL have a valid ad-hoc hardened-runtime signature. The
  builder SHALL record the consumer-compatible signature metadata and the
  complete observed entitlement mapping. It SHALL never report Developer ID or
  notarization.
- The generated `metadata/native-signing.json` member SHALL bind the detailed
  signing and entitlement observations into the signed payload closure.

## Deterministic output and consumer compatibility

- Members SHALL be sorted and encoded directly to the output file as bounded POSIX USTAR records with zero
  timestamps, numeric owner/group zero, empty owner/group names, normalized
  modes, no links or extension records, zero data padding and exactly two zero
  end blocks. Payload and archive bytes SHALL be hashed incrementally; the
  builder SHALL NOT materialize the complete payload or archive in memory.
- The manifest SHALL use `specfact-native-capsule-v1` exactly and remain
  byte-canonical JSON compatible with `native_capsule.py`.
- The closure SHALL partition all payload members, including generated signing
  metadata. File digests, modes, archive size/digest, and closure digest SHALL
  cover final bytes.
- The canonical manifest SHALL be signed with a maintainer-controlled Ed25519
  or RSA private key. Private key bytes SHALL never enter the payload, manifest,
  summary, or logs.
- Identical inputs and identities SHALL produce identical archive, manifest,
  signature, and aggregate summary bytes.

## Full-runtime bounded profile

The shared builder and consumer admit at most 200,000 payload files, 4 GiB of
aggregate payload bytes, a 4 GiB USTAR archive, 2 GiB per member, 240-byte paths,
32 path components and a 64 MiB authenticated manifest. These bounds are sized
for a sealed CPython plus analyzer dependency closure while preserving explicit
resource ceilings. The builder SHALL fail with a concrete
`native_capsule_schema_limit` reason when a complete runtime exceeds any bound.
It SHALL NOT omit files or allocate the complete payload/archive to force
admission. Passing these structural limits does not set production eligibility;
the real complete runtime and supported matrix still require acceptance.

## Candidate workflow

Any hosted builder SHALL use explicit native ARM64 macOS 14, 15, and 26 jobs.
It may upload immutable candidate artifacts for review. It SHALL have read-only
repository permissions and SHALL NOT push GHCR, publish a release, use release
credentials, or claim production support.

## Evidence and privacy

Tests cover determinism, manifest acquisition compatibility, closure faults,
architecture/signature/rpath faults, unsafe paths, and every current schema
limit. Output summaries contain only identities, counts, sizes, and digests.
Raw tool output and private receipts remain local and ignored.

## CI-only manifest signing correction — 2026-10-05

The `--unsigned` build path requires no private key and emits final deterministic
archive/manifest bytes with no signature sidecar. It retains every structural,
native signature, closure and resource check. Its summary explicitly records
`manifest_authenticated=false` and `production_eligible=false`. The signed path
remains compatible; actual publisher keys are used only in separate protected
CI/CD signing jobs. Fixture keys in unit tests do not authenticate release
artifacts. An unsigned build does not populate the customer catalog or admit a
platform. Build and signing separation is necessary but is not release acceptance.
