"""Human-gated protected OCI upload, followed by anonymous exact-blob verification."""

from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

from scripts.native_release.artifacts import REPOSITORY, read_bounded
from scripts.native_release.cli import PUBLIC_KEY
from scripts.native_release.release import ABIS, _artifact_set, catalog_entry, protected_source
from specfact_code_review.run import native_backend, native_capsule


# Share the exact signed schema and customer transport checks.
# pylint: disable=protected-access


def _signed_inputs(root: Path, public: bytes, source: str):
    release = native_capsule._json(read_bounded(root / "release.json", 64 * 1024))
    if native_capsule._canonical(release) != native_capsule._canonical(
        {"source_sha": source, "publication": "staged-only", "production_eligible": False}
    ):
        raise ValueError("publication source differs from protected staged release")
    artifacts = _artifact_set([root / "archives" / f"darwin-arm64-{abi}" for abi in ABIS])
    expected_entries = {}
    for name, artifact in artifacts.items():
        signature = read_bounded(artifact.directory / "manifest.sig", 64 * 1024).decode("ascii").strip()
        if read_bounded(artifact.directory / "manifest-public.pem", 64 * 1024) != public:
            raise ValueError("publication key differs from reviewed public key")
        native_capsule._authenticate(artifact.manifest, signature, public)
        entry = catalog_entry(artifact)
        packaged = native_backend._catalog_entry(root / "module", name, entry, offline=True)
        if (packaged.manifest, packaged.signature, packaged.public_key) != (artifact.manifest, signature, public):
            raise ValueError("publication packaged resources differ from signed archive")
        expected_entries[name] = entry
    catalog = native_capsule._json(
        read_bounded(root / "module/resources/contracts/native-capsule-catalog-v1.json", 1024 * 1024)
    )
    if native_capsule._canonical(catalog) != native_capsule._canonical(
        {"schema": "specfact-native-capsule-catalog-v1", "entries": expected_entries}
    ):
        raise ValueError("publication catalog differs from authenticated descriptors")
    return artifacts


def _anonymous_blob(entry: dict) -> None:
    credentials = {name: os.environ.pop(name) for name in ("GITHUB_TOKEN", "GH_TOKEN") if name in os.environ}
    try:
        ghcr = entry["ghcr"]
        reader = native_backend._open_registry_blob(
            repository=REPOSITORY,
            digest=ghcr["blob"]["digest"],
            size=ghcr["blob"]["size"],
            allowlist=tuple((row["host"], row["path_prefix"]) for row in ghcr["redirect_allowlist"]),
            max_redirects=4,
        )
        with reader:
            while reader.read(64 * 1024):
                pass
    finally:
        os.environ.update(credentials)


def publish_release(root: Path, public: bytes, context: Mapping[str, str]) -> None:
    source = protected_source(context)
    artifacts = _signed_inputs(root, public, source)
    for name, artifact in artifacts.items():
        tag = f"candidate-{source}-{name}"
        subprocess.run(
            [
                "oras",
                "push",
                "--artifact-type",
                "application/vnd.ai.nold.specfact.native-capsule.v1",
                f"ghcr.io/{REPOSITORY}:{tag}",
                "capsule.tar:application/vnd.ai.nold.specfact.native-capsule.v1.tar",
            ],
            cwd=artifact.directory,
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        _anonymous_blob(catalog_entry(artifact))
    # No production approval: immutable blobs are staged; the signed module still needs release.
    (root / "anonymous-publication-verified.txt").write_text(source + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    args = parser.parse_args()
    publish_release(args.release, read_bounded(PUBLIC_KEY, 64 * 1024), os.environ)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
