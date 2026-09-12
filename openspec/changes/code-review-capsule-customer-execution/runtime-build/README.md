# Runtime correction provenance

Recorded 2026-09-13, Europe/Berlin. These are new development artifacts for #466, not a signed module release or customer acceptance evidence.

The real analyzer entrypoint imports `beartype`, which was absent from every previous runtime closure. The only added distribution is public `beartype==0.22.9`: [PyPI metadata](https://pypi.org/pypi/beartype/0.22.9/json), accessed 2026-09-13. Its wheel has 1,333,658 bytes and SHA-256 `d16c9bbc61ea14637596c5f6fbff2ee99cbe3573e46a716401734ef50c3060c2`. All declared dependencies are inactive optional extras.

Each build context contains only its Dockerfile, that verified wheel, and the updated wheelhouse manifest. `reference-receipts.json` records exact Dockerfiles, OCI leaf identities, reference filesystem identities and publication state. Existing OCI layers remain unchanged; each new manifest adds two layers containing the wheel and wheelhouse manifest. No existing tag or artifact is replaced.

## Reproduction procedure

1. Retrieve the wheel from the URL in PyPI metadata and verify its byte count and SHA-256 before building. Add its verified descriptor to the baseline wheelhouse manifest and recompute the manifest's canonical digest.
2. Build each recorded Dockerfile using `docker build --platform linux/amd64`, without a repository mount or credentials in the build context.
3. In two independent containers per ABI, with `--network none`, run the sealed interpreter through `/opt/specfact/lib/ld-linux-x86-64.so.2 --library-path /opt/specfact/lib`. Set `PYTHONHOME=/opt/specfact/python`. With umask 022, create `/opt/specfact/analyzers` and run `python -m pip install --no-index --no-deps --no-compile --no-warn-script-location --target /opt/specfact/analyzers /opt/specfact/wheelhouse/*.whl`.
4. Commit each reference container locally, then run `measure_root.py` from standard input with the sealed interpreter's `-I -` flags, `--network none`, and `--user 1000:1000`. Compare both JSON outputs byte-for-byte.
5. Verify that the `bin`, `bootstrap`, `lib`, and `python` subroot identities exactly equal the previous signed lock. Only analyzer and wheelhouse identities may change.
6. Retrieve published OCI manifest/config bytes anonymously and verify their SHA-256 identities. Preserve raw bytes and their parsed objects in `<abi>-oci.json`; preserve measurements as `<abi>-root-manifest.json` and `<abi>-root-manifest-b.json`.
7. Run `refresh_lock.py --repo <baseline checkout> --build-root <receipts directory>`. It refuses any baseline except the reviewed lock, mismatched raw OCI objects, changed prior layers, unequal measurements, or unexpected immutable subroot changes. Review the resulting lock and resource bindings before canonical module signing/publication.

Reference installation used root inside disposable containers; filesystem measurement used UID 1000. This establishes reproducible build identities, not non-root customer installation. The hosted customer matrix must independently reproduce the installed root under the production downloader and installer.

Do not derive Linux identity from `docker cp` output on macOS: extraction changes symlink modes. The recorded identities were measured inside Linux. Old manifests were retained throughout; no observed failing customer digest was substituted into an old lock.

Python 3.11 and 3.12 development tags were published and anonymously verified. Python 3.13 publication was blocked by automatic approval review and awaits explicit authorization; its recorded leaf identity comes from a local OCI export. Until publication and the complete hosted matrix pass, these assets are not accepted for release.

Rollback uses the previous immutable locks and normal signed revert/publication procedures. Do not delete or rewrite historical artifacts.

## Revised runtime: complete runner imports

The first hosted run after the beartype correction reached the real runner and reported missing `yaml`. PyYAML 6.0.3 was retrieved from [PyPI metadata](https://pypi.org/pypi/PyYAML/6.0.3/json), accessed 2026-09-13, and each ABI wheel's exact size and SHA-256 were verified. `pyyaml-reference-receipts.json` records these public wheel descriptors and new v2 artifacts. This is the second correction applied to the first reference builds; reconstruct the local v1 image from its recorded original-image Dockerfile first, then build the recorded v2 Dockerfile. No v1 publication is required to reproduce locally.

Run the same two-container measurement process, additionally asserting `yaml.__version__ == "6.0.3"`. `refresh_lock.py --addition pyyaml` accepts only the reviewed beartype-corrected lock and the three approved PyYAML wheel identities. The real runner import was also exercised in a disposable Python 3.12 reference image as UID 1000 with network disabled; it passed. The image used only for this import smoke was not published.

The owner explicitly approved all three v2 development runtime publications. All three are now published under `customer-466-cp311-v2`, `customer-466-cp312-v2`, and `customer-466-cp313-v2`; anonymous reads of manifest and config bytes matched the locally exported identities. The earlier pending cp313-v1 request was superseded. Public signed-module release and the three-ABI analyzer matrix remain separate acceptance gates.
