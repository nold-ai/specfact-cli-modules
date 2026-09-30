# Local macOS ARM64 packaging candidate

Experimental feasibility tooling only. No publication command, runtime selection,
trusted native evidence, dependency admission or production eligibility is provided.
The verifier never extracts or executes archive contents. Its expected payload is
operator input, not an authenticated dependency closure. Keep this operator-owned
tree immutable throughout comparison. Expected regular files must have exactly
one filesystem link; hard-link aliases inside or outside the tree are rejected. Filesystem reads are not a TOCTOU-resistant
seal; concurrent substitution is outside this feasibility tool's authority. Native provenance remains
an unverified operator claim even when packaging passes.

## Reproduce on an ARM64 Mac

Run from the worktree root with Docker Desktop started, Command Line Tools installed
and the existing `.venv`. This builds a harmless native hello fixture locally, gives
it an **ad-hoc** signature (not Developer ID/notarization), and runs only that locally
compiled input. Docker performs COPY-only assembly, never native execution.

```bash
set -eu
test "$(uname -s)" = Darwin
test "$(uname -m)" = arm64
proof_dir="$(mktemp -d /private/tmp/specfact-460-candidate-XXXXXX)"
mkdir -p "$proof_dir/context/payload"
cat > "$proof_dir/hello.c" <<'C'
#include <stdio.h>
#include <sys/utsname.h>
int main(void) {
    struct utsname u;
    if (uname(&u)) return 1;
    printf("specfact-460-copy-proof %s %s\n", u.sysname, u.machine);
    return 0;
}
C
xcrun clang -arch arm64 "$proof_dir/hello.c" -o "$proof_dir/context/payload/hello"
codesign --force --sign - "$proof_dir/context/payload/hello"
codesign --verify --strict "$proof_dir/context/payload/hello"
"$proof_dir/context/payload/hello"
cp openspec/changes/code-review-native-platform-execution/candidate-build/Dockerfile "$proof_dir/context/Dockerfile"
docker buildx build --platform darwin/arm64 --network none \
  --provenance=false --sbom=false \
  --output "type=oci,dest=$proof_dir/candidate.oci.tar" \
  --metadata-file "$proof_dir/build-metadata.json" "$proof_dir/context"
.venv/bin/python scripts/macos_capsule_candidate.py "$proof_dir/candidate.oci.tar" \
  --expected-payload "$proof_dir/context/payload" > "$proof_dir/verification.json"
cat "$proof_dir/verification.json"
printf 'Retained local proof: %s\n' "$proof_dir"
```

Expected: `status=PASS`, actual config/index `darwin/arm64`, and
`production_eligible=false`. The source executable runs on macOS; Docker's Linux
server identity never substitutes for the payload identity. Compare the reported
manifest/config digests with `build-metadata.json` for an independent export receipt.
The verifier checks blob sizes/digests, gzip layer diff_id, exact file membership,
bytes and file permission modes. It also compares directory membership; directory
permission modes are not an acceptance claim.

## Deliberate bounds and failure behavior

Only ordinary ustar (`ustar-NUL`/`00`) or GNU (`ustar-space`/`space-NUL`)
file/directory TAR headers with complete framing, two zero end
blocks and zero trailing padding are accepted; the unused final twelve bytes of
each ordinary header must also be zero; extended and sparse headers are
unsupported. Numeric fields require unsigned octal text with NUL/space padding;
signed, base-256 and hidden post-terminator bytes are rejected. Required numeric
fields must contain an octal digit; unused device fields may be padding-only.
Present non-null history must contain one non-empty-layer entry for the single
rootfs layer; absent/null history is accepted. Gzip flags and optional header CRC are validated; truncation,
concatenated members and any trailing bytes are rejected. The outer OCI tar must
contain one manifest and one single-member gzip layer. The layer must contain a
`/proof` tree matching the operator-provided expected payload exactly. Limits are
32 MiB for archive/input reads and cumulative tar contents, 16 MiB for decompressed
layer/expected payload, and 256 members per tree/archive. This is a tiny proof tool,
not a full runtime packager. Links, special/sparse files, malformed/truncated framing, nonzero trailing data,
duplicate member names,
noncanonical raw header paths, nonzero bytes after any text-field NUL terminator
(including link name, owner name and group name),
non-UTF-8 metadata and duplicate JSON keys fail closed. Image configuration, index, manifest and descriptor
fields and formats are checked against the locally stored OCI v1.1.1 schemas
(`scripts/schemas/`), using the explicitly declared Hatch JSON Schema dependency;
no remote schema is resolved. Map keys unmatched by the schema property pattern
(including empty/newline-only names) are explicitly rejected. A declared index `mediaType` must be
`application/vnd.oci.image.index.v1+json`; omission is accepted. Outer files must be exactly
`oci-layout`, `index.json` and the three referenced blobs. Embedded descriptor
`data` and index/manifest `subject` fields are unsupported and rejected; only optional `blobs`
and `blobs/sha256` parent directory headers are allowed. Malformed inputs yield
`ValueError` through the Python API or exit 1 with failure JSON through the CLI.

No archive is extracted, no payload is launched, and no signing assertion is
trusted. Full native build/signing/notarization, dependency closure, confinement
and customer-installation evidence remain separate production gates. Repeat local
assembly with the same finalized inputs to investigate reproducibility; this tool
does not claim reproducible native builds or authenticated provenance.

Nothing is pushed. Rollback is simply to discard the explicitly printed temporary
proof directory after reviewing its contents; retained Linux assets are unaffected.
