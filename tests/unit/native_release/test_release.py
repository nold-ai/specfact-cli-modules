from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519

from scripts.native_release import release
from specfact_code_review.run import native_backend, native_capsule


def test_signed_catalog_round_trips_through_unchanged_customer_loader(release_inputs, tmp_path, monkeypatch):
    directories, receipts, key, public, context = release_inputs
    output = tmp_path / "release"
    release.stage_release(release.StageRequest(directories, receipts, output, public, context), lambda: key)
    monkeypatch.setattr(native_backend, "files", lambda _name: output / "module")
    catalog = native_backend._packaged_artifact_catalog(offline=True)
    assert set(catalog) == {f"darwin-arm64-{abi}" for abi in release.ABIS}
    for artifact in catalog.values():
        document = native_capsule._authenticate(artifact.manifest, artifact.signature, public)
        assert document["backend"] == native_backend.BACKEND_VERSION
        assert artifact.reader is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("GITHUB_REF", "refs/pull/498/merge"),
        ("GITHUB_REF_PROTECTED", "false"),
        ("GITHUB_EVENT_NAME", "pull_request"),
        ("GITHUB_WORKFLOW_SHA", "b" * 40),
        ("GITHUB_REPOSITORY", "attacker/fork"),
    ],
)
def test_untrusted_context_never_loads_signing_key(release_inputs, tmp_path, field, value):
    directories, receipts, _key, public, context = release_inputs
    context[field] = value

    def forbidden_key():
        pytest.fail("signing authority accessed before context validation")

    with pytest.raises(ValueError, match="protected"):
        release.stage_release(
            release.StageRequest(directories, receipts, tmp_path / "release", public, context), forbidden_key
        )
    assert not (tmp_path / "release").exists()


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "source", "archive", "check", "integer"])
def test_incomplete_or_substituted_matrix_never_loads_key(release_inputs, tmp_path, mutation):
    directories, receipts, _key, public, context = release_inputs
    document = json.loads(receipts.read_bytes())
    mutate_receipt(document, mutation)
    receipts.write_text(json.dumps(document))

    def forbidden_key():
        pytest.fail("signing authority accessed before matrix validation")

    with pytest.raises(ValueError):
        release.stage_release(
            release.StageRequest(directories, receipts, tmp_path / "release", public, context), forbidden_key
        )
    assert not (tmp_path / "release").exists()


def test_foreign_signing_key_cannot_leave_partial_release(release_inputs, tmp_path):
    directories, receipts, _key, public, context = release_inputs
    with pytest.raises(ValueError, match="key"):
        release.stage_release(
            release.StageRequest(directories, receipts, tmp_path / "release", public, context),
            ed25519.Ed25519PrivateKey.generate,
        )
    assert not (tmp_path / "release").exists()
    assert not list(tmp_path.glob(".release-*"))


def test_duplicate_abi_is_rejected(release_inputs, tmp_path):
    directories, receipts, key, public, context = release_inputs
    directories[-1] = directories[0]
    with pytest.raises(ValueError, match="ABI"):
        release.stage_release(
            release.StageRequest(directories, receipts, tmp_path / "release", public, context), lambda: key
        )


def test_existing_output_is_never_replaced(release_inputs, tmp_path):
    directories, receipts, key, public, context = release_inputs
    output = tmp_path / "release"
    output.mkdir()
    (output / "owner-data").write_text("retain")
    with pytest.raises(ValueError, match="exists"):
        release.stage_release(release.StageRequest(directories, receipts, output, public, context), lambda: key)
    assert (output / "owner-data").read_text() == "retain"


def mutate_receipt(document, mutation):
    if mutation == "missing":
        document.pop()
        return
    if mutation == "duplicate":
        document[-1] = document[0]
        return
    if mutation == "source":
        document[0]["source_sha"] = "b" * 40
        return
    if mutation == "archive":
        document[0]["archive_sha256"] = "c" * 64
        return
    document[0]["checks"][release.REQUIRED_CHECKS[0]] = 1 if mutation == "integer" else False


def test_concurrent_empty_output_is_not_replaced(release_inputs, tmp_path):
    directories, receipts, key, public, context = release_inputs
    output = tmp_path / "release"

    def concurrent_writer():
        output.mkdir()
        return key

    with pytest.raises(ValueError, match="exists"):
        release.stage_release(release.StageRequest(directories, receipts, output, public, context), concurrent_writer)
    assert output.is_dir()
    assert not list(output.iterdir())
