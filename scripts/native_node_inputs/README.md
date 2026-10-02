# Native BasedPyright input preparation

This maintainer path packages upstream Node 24.16.0 for Darwin ARM64 and the
BasedPyright 1.39.10 npm distribution. It does not install the PyPI BasedPyright
wrapper or `nodejs-wheel-binaries`. The pinned optional `fsevents` package stays
in the npm lock for audit; it is omitted from the one-shot analyzer payload.

Download the two archives from the committed upstream URLs, then authenticate the
Node checksum list using the official Node release keyring before testing the
runtime. The packager itself runs offline and verifies its committed content pins:

```sh
python scripts/native_node_package.py \
  --node-archive /absolute/path/node-v24.16.0-darwin-arm64.tar.gz \
  --basedpyright-archive /absolute/path/basedpyright-1.39.10.tgz \
  --output /absolute/path/new-native-node-runtime
```

The output directory must not exist. Its parent must be an existing trusted
maintainer directory. Packaging validates both inputs before writing, normalizes
payload modes, writes the manifest last, and removes its own output on ordinary
write failure. This is a maintainer preparation tool, not an atomic shared-cache
installer: crash/interruption residue must be discarded, and the output must not
be consumed until packaging succeeds. It does not provide hostile same-user
filesystem-race protection or verification-to-launch guarantees.

The manifest binds every payload file to its hash and mode, records upstream
input identities, and keeps `dependency_admitted=false` and
`production_eligible=false`. It is not a signed admission manifest. All generated
payloads belong under ignored `.specfact/` or a disposable external directory.

For explicit compatibility testing of repository-authored fixtures only:

```sh
/absolute/path/new-native-node-runtime/bin/node \
  /absolute/path/new-native-node-runtime/basedpyright/index.js \
  --project /absolute/path/controlled-fixture/pyrightconfig.json --outputjson
```

This invocation runs with maintainer user permissions. It is not used by the
production review command and does not establish sandbox or project-corpus
acceptance. Customers will receive the final verified runtime through SpecFact;
these maintainer steps are not customer installation requirements.

## Upstream signature verification observed on 2026-10-02

- Node release-key repository revision:
  `481637f813e912c4aa3622d7964ab426c97b8e8d`.
- Keyring SHA-256:
  `610b8d249da3d5733f5a128def2dd0294dbbf5b5713e6ca2529db8db419dee00`.
- Valid release signature fingerprint:
  `5BE8A3F6C8A5C01D106C0AD820B1A390B168D356`.
- `SHASUMS256.txt` SHA-256:
  `e20ebbf68d33f42d196a7a11b8a91d422fa37b759c0a51aa4857977135cc5e95`.
- The signed checksum row matched the packager's committed Node archive hash.

Reproduce signature verification with an explicit keyring, without importing it
into a personal keychain:

```sh
gpgv --keyring /absolute/path/node-release-pubring.kbx \
  /absolute/path/SHASUMS256.txt.sig /absolute/path/SHASUMS256.txt
```

A recorded verification is not an automatic future verification step. Final
runtime admission must repeat publisher/content verification and audit licenses,
Mach-O loading, vulnerability policy and signing of the assembled capsule.

Sources: [Node release verification](https://github.com/nodejs/node#verifying-binaries),
[immutable keyring source](https://github.com/nodejs/release-keys/tree/481637f813e912c4aa3622d7964ab426c97b8e8d),
[Node release files](https://nodejs.org/dist/v24.16.0/),
[BasedPyright metadata](https://registry.npmjs.org/basedpyright/1.39.10).
