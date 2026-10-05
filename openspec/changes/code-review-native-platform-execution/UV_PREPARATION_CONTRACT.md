# Pinned native uv launch adapter

The Darwin candidate uses uv 0.12.13 from upstream commit
`0ebbd9274a55a8a53a13970be3b97e4209598e17`. Its reviewed distribution replaces
Python interpreter probes and build-hook launches with private broker requests.
The adapter preserves arguments, selected private environment, output and exit
status. Every Python child remains directly owned, traced and confined by the
broker. No host subprocess fallback is allowed inside the capsule.

The upstream isolated probe (`-I -B -c`) starts with the already isolated fixed
capsule interpreter. It receives its selected private environment's site only,
excluding inherited project import overlays. Its own explicit query-script
directory remains inside the worker's inherited filesystem grants.

Native manager code may acquire artifacts; project/build children receive no
network credentials or direct network permission. Other native subprocess
sites remain kernel-blocked until explicitly adapted and validated. uv sync
must preserve an existing lock, selected groups/extras and project configuration
in a disposable snapshot; absent locks may be resolved there. SDK and arbitrary
external-tool requirements remain actionable incomplete evidence.

The sealed Rust manager runs `sync` against a writable private snapshot and
uses an invocation-private cache and environment. It installs a non-editable
copy for reusable imports. Preparation harvests only that environment's site
after successful exit, then inventories it in a fresh no-network sealed worker.
The caller's lock and checkout are unchanged. A generated resolution lock is
retained in the local artifact and digest-bound; offline reuse verifies it.

Building uv is maintainer work, using a pinned Rust toolchain and upstream lock.
Customers receive its verified, prebuilt ARM64 image and need no local compiler.
Source, patch, license, binary digest and native signature belong in final
artifact provenance. Focused adapter tests do not establish full runtime
admission or replace the manager corpus and lifecycle matrix.

## Maintainer build

The maintainer supplies a local upstream uv checkout at the exact 0.12.13 commit,
a local Rust 1.96.0 toolchain, and a populated offline Cargo home. The builder
rejects an incorrect commit, dirty checkout (including untracked source files),
changed Cargo.lock, substituted or missing repository patch/bridge, and existing
output. It copies the clean tracked upstream source into a disposable directory,
applies only the repository's fixed launch patch, and installs only the reviewed
bridge at its fixed destination. It never edits the supplied checkout.

The build invokes Cargo with `--locked --offline --release --bin uv
--no-default-features` and a private target directory. It requires an ARM64
Mach-O executable, then signs it ad hoc with hardened runtime and identifier
`ai.nold.specfact.managed-uv` and verifies the resulting signature. The output
contains the binary, upstream MIT and Apache licenses, the reviewed patch and
bridge, and machine-readable provenance with source/toolchain/lock/input/output
SHA-256 digests, exact build arguments, signature mode and identifier. No
publisher key, module signature, or customer-side compilation participates.
