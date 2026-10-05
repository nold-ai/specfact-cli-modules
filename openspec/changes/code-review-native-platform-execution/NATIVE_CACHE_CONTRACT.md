# Authenticated native cache candidate

Owner-authorized #460 remainder, 2026-10-03 (Europe/Berlin). The original candidate remains in `scripts/native_capsule_cache.py` with its focused tests. The bounded package integration ports those invariants into `specfact_code_review.run.native_capsule`, adds ABI-aware selection in `native_backend`, and connects only the existing `runner.py` platform seam. It does not complete the parent change.

## Specification before implementation

Authenticate caller-supplied manifest bytes using independently pinned public PEM: Ed25519 exact-byte verification or RSA PKCS#1 v1.5 / SHA-256, matching SpecFact crypto_validator. Never trust keys from artifact metadata. Reject duplicate JSON keys and unknown fields. Bind Darwin ARM64, selected CPython 3.11–3.13 ABI, exact backend/policy versions, archive size/hash, file size/hash/mode and a hashed component-to-file closure. Closure authenticity is not dependency-policy approval.

Accept bounded streamed plain USTAR archives only: canonical lowercase ASCII paths, unique regular files in the exact signed manifest order, exact signed modes and sizes, exactly two zero end blocks, and no directories, links, devices, PAX, GNU, sparse records, descriptors, nonzero padding or trailing bytes. Authenticate the manifest before opening the reader, then hash the archive and each file incrementally while extracting once into anchored no-follow staging files. No whole-archive or whole-file allocation is permitted. Progress reports downloading, verifying and ready; interruption never publishes a partial cache. A private anchored no-follow cache root and per-identity flock serialize cooperative installs; fsync files/directories before atomic rename. Existing invalid final entries fail closed. Orphan staging directories are never selected.

Offline reuse must reauthenticate supplied manifest and recheck every file, parent directory, mode, size, digest, link count and exact tree membership. Retain verified opened descriptors and inode/device identities only for authenticated executable/native members until caller closes the lease; ordinary data files are verified with bounded reads and closed immediately. Unsupported backend/policy selection and missing offline cache yield actionable INCOMPLETE capability evidence. production_eligible and artifact_publication_production remain false.

## Integration limits

Injected reader is the concrete acquisition API. Core marketplace_client resolves registry URLs but currently buffers requests.get(...).content; it cannot supply bounded streaming without a future adapter. No CLI wiring, registry selection, GHCR credentials, secret access, signing keys, Docker, publication or native execution occurs here. Test keys are ephemeral fixture keys only.

Retained descriptors close pathname replacement for descriptor readers; they do not freeze same-user writable inodes or prove Mach-O execution identity. The parent must connect broker image admission, code-signature identity, dyld closure and launch-time policy to this lease, enforce an immutable execution snapshot, and repeat independent cold/offline installation on the required macOS/ABI matrix. No claim that verification-to-execution race is closed. Caller owns public-key selection, freshness/revocation, approved backend/policy and independently reviewed closure completeness. This schema is a candidate wire format, not a released signed manifest.

Failure mitigation: corrupt final cache fails closed (explicit operator removal required); interrupted staging is ignored (operator cleanup only); same-user mutation requires parent immutable-image admission. The full-runtime profile bounds archive and aggregate unpacked bytes to 4 GiB each, files to 200,000, each member to 2 GiB, canonical paths to 240 bytes and 32 components, and authenticated manifest bytes to 64 MiB. Extraction memory is bounded by the authenticated manifest plus a 64 KiB transfer buffer and parser metadata; payload bytes are never accumulated. Before opening the reader, available cache-filesystem space must cover signed unpacked bytes plus a 64 MiB reserve. No deadlines are enforceable against a blocking injected reader: the production reader must enforce connect/read deadlines and cancellation. Rollback restores the prior bounded candidate without treating its smaller limits as production acceptance.

## Private allowlisted test evidence

Recorded 2026-10-03 (Europe/Berlin); allowlisted summary only. No broad gates or shared analyzer writers were run. Host: Darwin ARM64, macOS 27.0.1, Python 3.14.7. Tools: pytest 9.1.1, Ruff 0.16.9, BasedPyright 1.39.10 (Pyright 1.1.412). ABI tests check authenticated metadata selection for 3.11/3.12/3.13; this host run is not interpreter or supported-OS acceptance.

Commands ran from the authorized worktree:

- RED: `.venv/bin/python -m pytest tests/unit/test_native_capsule_cache.py -q -o addopts='' -p no:cacheprovider --tb=no` → exit 1, 30 failed in 1.66 s against the explicit NotImplementedError interface. Earlier absent-file collection run: 30 errors; not counted as behavioral RED.
- Initial GREEN: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/unit/test_native_capsule_cache.py -q -o addopts='' -p no:cacheprovider --tb=short` → exit 0, 30 passed in 0.48 s.
- Adversarial extension RED with that focused command: exit 1, 1 failed / 38 passed in 0.52 s; unused regular-member TAR link descriptor was accepted. Fixed by explicit descriptor rejection.
- Concurrency investigation: 1 failed / 40 passed in 0.57 s; repeated two-test loop failed at repetition 3. Diagnostic read-only instrumentation observed ENOENT on nonexclusive O_CREAT lock open while the anchored private root already contained that lock. No claim about an independently established kernel cause. Replaced with O_CREAT|O_EXCL creation followed by an existing-file open on EEXIST.
- Concurrency GREEN: an in-process Python loop repeated `pytest.main(['tests/unit/test_native_capsule_cache.py::test_concurrent_install_once', 'tests/unit/test_native_capsule_cache.py::test_independent_processes_install_once', '-q', '-o', 'addopts=', '-p', 'no:cacheprovider', '--tb=short'])` 20 times, stopping on nonzero exit → all 40 test executions passed. Each repetition exercised 12 calls through six threads and four independent forked installers, with exactly one reader call per cache.
- Final GREEN with the focused command above: exit 0, **42 passed in 0.59 s**. Includes real installer process death after extraction, orphan rejection offline, successful retry, cleanup-error descriptor release, signature forgery/key substitution, duplicate JSON, all three ABI selections, digest/mode/size/closure binding, hardlinks, symlink substitution at open, late hardlink during digest, post-verification pathname replacement, archive/device/PAX/extra-byte rejection and oversized reader rejection.
- `.venv/bin/ruff format --check scripts/native_capsule_cache.py tests/unit/test_native_capsule_cache.py` → exit 0, two files already formatted.
- `.venv/bin/ruff check scripts/native_capsule_cache.py tests/unit/test_native_capsule_cache.py` → exit 0, all checks passed.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/basedpyright scripts/native_capsule_cache.py tests/unit/test_native_capsule_cache.py --level error` → exit 0, zero errors/warnings/notes.
- `openspec validate code-review-native-platform-execution --strict` → exit 0, change valid. The change remains active and incomplete.

Exact final tested source SHA-256:

- scripts/native_capsule_cache.py: `810600661192ca928febe8ac09c43b65283e91f682bb092b0d5912bc04b78a5c`
- tests/unit/test_native_capsule_cache.py: `ee880c17b268ec93b77a661f9b446c63dac6c78bcf5ad68266306bb3a19d0c15`

No commit, push, publication, signing, shared review JSON, module/runtime/core modification or parent completion is claimed. Repository-wide gates and protected review authority remain deferred under the user's explicit scope restrictions. Confidence: High for the exercised acquisition candidate; Low for production admission, which has not been attempted.


## Concrete integration surface

`acquire(cache_root, manifest_bytes, detached_signature_base64, pinned_public_pem_bytes, abi="3.11", backend=approved_backend_version, policy=approved_policy_version, reader=bounded_stream_factory, offline=False)` returns a context-managed Lease with `fds`, `code_identities`, `identity`, `path` and allowlisted evidence. Keep the lease open for descriptor-based consumption; `path` is diagnostic, not execution authority. Close releases every retained handle. Caller must provide an existing symlink-free parent and owner-owned 0700 cache root (the leaf is created automatically). Explicit error type is `IncompleteError`; its evidence is always INCOMPLETE and nonproduction. Other validation errors fail acquisition and never execute anything.

Default progress emits JSON phase/byte counts to stderr; callers may supply a `(phase, byte_count)` callback. Offline mode never invokes the reader. The candidate takes no URL, credential or artifact-supplied key. It consumes exactly the signed archive size using `read(n)` requests of at most 64 KiB, verifies ordinary USTAR headers in manifest order, writes and hashes each member incrementally, verifies zero padding and exactly two zero end blocks, then probes one byte for EOF. It never invokes unbounded `read()` or `read(-1)`. Signed file modes are 0400 or 0500; directories are 0700. No cache metadata files are authoritative: each invocation takes and authenticates the selected signed manifest again.

Authenticated `closure` partitions every file among named components and binds its canonical JSON SHA-256. This proves exact listed-file closure, not that omitted upstream dependencies, licensing/provenance, package metadata, Apple code signatures, quarantine, hardened-runtime settings, entitlements or backend capability have been independently approved. `backend` and `policy` compare against caller selections, rather than a newly invented approval list.

Atomicity covers cooperating installers and publication by same-filesystem rename after fsync; it is not protection against a hostile process with the same UID. Root ancestors must be trustworthy and local flock/rename/fsync semantics must be supported. Root or lock substitution by the same UID, in-place writes after verification and native loader path reopening require the parent's independent immutable-image/owned-broker controls. Retained fds do not grant native execution or protected evidence authority. Cleanup failure leaves unselectable staging and releases controller descriptors; caches never select or automatically delete another installer's orphan. Crash before publication may leave only such staging; explicit operator cleanup is bounded to nonactive orphan names.

## Bounded package integration

The package manifest schema is `specfact-native-capsule-v1`. It additionally binds the exact `darwin-arm64-cp311`, `darwin-arm64-cp312` or `darwin-arm64-cp313` environment and authenticated ad-hoc hardened-runtime metadata for every executable. Cold acquisition validates native signatures before atomic publication; offline reuse validates them again. The default inspector uses the fixed macOS `/usr/bin/codesign` path with a minimal environment and timeout. Tests may inject an inspector only to exercise deterministic signing records on non-Darwin hosts.

The admitted artifact catalog is deliberately empty. Darwin ARM64 runner selection therefore returns `native_capsule_artifact_not_admitted:<environment-id>` and does not enter Linux materialization or development-host compatibility. A verified cache lease is not yet an execution backend: if a future catalog entry is introduced before launch admission is integrated, the runner closes it and returns `native_capsule_execution_backend_not_admitted:<environment-id>`. Both dispositions remain incomplete and nonproduction.

## Automatic bounded GHCR acquisition

The packaged catalog remains empty until a real capsule is published. Each future entry is strict, versioned module data that binds one exact Darwin ARM64 CPython environment to the packaged signed manifest, detached signature and independently pinned public key resources; the exact `managed-v1` backend and `deny-v1` policy; and one `ghcr.io` repository, SHA-256 blob digest and byte size. Catalog loading rejects unknown fields, duplicate environments, unsupported platforms or ABIs, unsafe resource names, manifest/catalog identity disagreement, non-GHCR registries, mutable references, malformed digests and sizes, and redirect rules outside the exact GHCR blob path plus explicitly admitted GitHub package-storage paths. These substitutions fail before any network request.

Online acquisition constructs the immutable `/v2/<repository>/blobs/<sha256>` locator from authenticated catalog fields. It uses bounded HTTPS redirects and connect/read deadlines, supports the exact GHCR anonymous Bearer challenge and an existing `GITHUB_ACTOR`/`GITHUB_TOKEN` credential, and never forwards credentials or registry bearer tokens to redirect storage hosts. The challenge realm, service and repository pull scope are allowlisted. The response is exposed as a closeable, cancellable streaming reader: reads must have a positive bound, never buffer the archive, reject content-length disagreement, oversize, truncation and digest mismatch, and close the underlying response on every terminal path. Progress remains aggregate byte counts only. Offline verified-cache reuse does not construct or open a network reader.
## Registry and path compatibility — 2026-10-05

Bearer-token responses remain streamed until the bounded token reader has
consumed and validated them. Requests' eager body handling cannot drain the
stream first or bypass its response-size limit. A relative caller cache root
is anchored to an absolute path before returning staged or reusable leases;
existing no-follow directory and inode validation remains mandatory.
