from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from scripts.native_release import artifacts


def test_exact_unsigned_archive_is_validated_without_execution(release_artifact):
    built = release_artifact()
    result = artifacts.inspect_archive(built.archive.parent)
    assert result.document["environment_id"] == "darwin-arm64-cp312"
    assert result.manifest_sha256 == hashlib.sha256(built.manifest.read_bytes()).hexdigest()


@pytest.mark.parametrize("name", ["bin/specfact-native-broker", "tools/node", "python/bin/python3"])
def test_substituted_loader_entitlement_is_rejected(release_artifact, name):
    built = release_artifact(altered_entitlement=name)
    with pytest.raises(ValueError, match="entitlement"):
        artifacts.inspect_archive(built.archive.parent)


def test_archive_mutation_is_rejected_before_signing(release_artifact):
    built = release_artifact()
    with built.archive.open("r+b") as stream:
        stream.seek(512)
        stream.write(b"changed")
    with pytest.raises(ValueError, match="digest"):
        artifacts.inspect_archive(built.archive.parent)


def test_symlinked_archive_is_rejected(release_artifact, tmp_path):
    built = release_artifact()
    saved = tmp_path / "saved.tar"
    built.archive.rename(saved)
    built.archive.symlink_to(saved)
    with pytest.raises(ValueError, match="regular"):
        artifacts.inspect_archive(built.archive.parent)


def test_false_native_signature_mode_is_rejected(release_artifact):
    built = release_artifact()
    document = json.loads(built.manifest.read_bytes())
    document["native_signatures"]["tools/node"]["mode"] = "developer-id"
    built.manifest.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="signing"):
        artifacts.inspect_archive(built.archive.parent)


@pytest.mark.parametrize("field", ["entitlements", "signature"])
def test_integer_cannot_impersonate_boolean_in_signing_profile(field):
    signatures = {name: {"hardened_runtime": True} for name in artifacts.REQUIRED_IMAGES}
    images: dict[str, dict[str, Any]] = {
        name: {
            "signature": dict(record),
            "entitlements": dict(artifacts.LOADER_ENTITLEMENTS) if name in artifacts.LOADER_IMAGES else {},
        }
        for name, record in signatures.items()
    }
    record = images["python/bin/python3"]
    if field == "entitlements":
        record[field]["com.apple.security.cs.disable-library-validation"] = 1
    else:
        record[field]["hardened_runtime"] = 1
    metadata = json.dumps({"schema": "specfact-native-signing-v1", "images": images}).encode()
    with pytest.raises(ValueError, match="profile"):
        artifacts.validate_loader_profile(metadata, signatures)
