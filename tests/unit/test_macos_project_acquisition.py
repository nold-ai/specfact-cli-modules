"""Trusted acquisition produces authenticated offline-only manager inputs."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import io
import json
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "scripts/macos_managed_boundary/project_acquisition.py"
CORPUS = Path(__file__).resolve().parents[2] / "tests/fixtures/portable-runtime/corpus.json"
SECRET = b"test-only-acquisition-authenticator"


def api() -> Any:
    spec = importlib.util.spec_from_file_location("macos_project_acquisition_test", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _entry(manager: str = "pip") -> dict[str, Any]:
    corpus = json.loads(CORPUS.read_text())
    return next(item for item in corpus["repositories"] if item["manager"] == manager)


def _archive(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for name, data in {
            "project/pyproject.toml": b"[project]\nname='fixture'\nversion='1.0'\n",
            "project/src/fixture.py": b"VALUE = 1\n",
            "project/tests/test_fixture.py": b"def test_fixture(): assert True\n",
        }.items():
            details = tarfile.TarInfo(name)
            details.size = len(data)
            details.mode = 0o644
            details.mtime = 0
            bundle.addfile(details, io.BytesIO(data))
    return archive


def _wheel(tmp_path: Path, *, filename: str = "fixture_dep-2.0-py3-none-any.whl") -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / filename
    path.write_bytes(b"wheel fixture")
    return {
        "package": "fixture-dep",
        "version": "2.0",
        "filename": filename,
        "url": f"https://files.pythonhosted.org/packages/aa/{filename}",
        "path": path,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _sign(payload: bytes) -> dict[str, str]:
    """Explicit test-only signer; production uses the SpecFact release key."""
    return {
        "algorithm": "test-hmac-sha256",
        "key_id": "fixture",
        "value": hmac.new(SECRET, payload, hashlib.sha256).hexdigest(),
    }


def _verify(payload: bytes, signature: dict[str, str]) -> bool:
    expected = hmac.new(SECRET, payload, hashlib.sha256).hexdigest()
    return (
        signature.get("algorithm") == "test-hmac-sha256"
        and signature.get("key_id") == "fixture"
        and hmac.compare_digest(signature.get("value", ""), expected)
    )


def _verify_source(request: dict[str, Any], archive_sha256: str, tree_sha256: str) -> dict[str, Any]:
    """Explicit test double for trusted git/GitHub verification."""
    return {
        "schema": "specfact-trusted-source-fetch-v1",
        "method": "git-checkout",
        "source_url": request["source"]["url"],
        "archive_url": request["source"]["archive_url"],
        "commit": request["source"]["commit"],
        "git_tree": "1" * 40,
        "archive_sha256": archive_sha256,
        "tree_sha256": tree_sha256,
        "authenticated_transport": True,
    }


def _bundle(tmp_path: Path, manager: str = "pip") -> tuple[Any, Path, dict[str, Any]]:
    module = api()
    request = module.build_acquisition_request(_entry(manager), "3.13")
    destination = tmp_path / "staged"
    descriptor = module.create_acquisition_bundle(
        request,
        _archive(tmp_path),
        artifacts=[_wheel(tmp_path)],
        destination=destination,
        signer=_sign,
        source_verifier=_verify_source,
    )
    return module, destination, descriptor


def test_request_binds_pinned_source_abi_and_exact_manager_versions() -> None:
    module = api()
    expected = {"pip": "26.2.1", "hatch": "1.18.0", "uv": "0.12.13", "poetry": "2.4.3"}
    for manager, version in expected.items():
        entry = _entry(manager)
        request = module.build_acquisition_request(entry, "3.13")
        assert request["source"]["url"] == entry["url"]
        assert request["source"]["commit"] == entry["commit"]
        assert request["source"]["archive_url"].endswith(f"/archive/{entry['commit']}.tar.gz")
        assert request["manager"] == {"name": manager, "version": version}
        assert request["selection"] == {"groups": entry["groups"], "environment": entry["environment"]}
        assert request["abi"] == "cp313"
        assert request["network"] == "trusted-acquisition-only"
        assert request["execute_project_code"] is False


def test_bundle_authenticates_source_archive_tree_lock_and_wheelhouse(tmp_path: Path) -> None:
    module, destination, descriptor = _bundle(tmp_path)
    verified = module.verify_acquisition_bundle(destination, verifier=_verify)
    assert verified == descriptor
    assert descriptor["schema"] == "specfact-macos-project-acquisition-v1"
    assert len(descriptor["source"]["archive_sha256"]) == 64
    assert len(descriptor["source"]["tree_sha256"]) == 64
    assert descriptor["source"]["trusted_fetch"]["method"] == "git-checkout"
    assert descriptor["source"]["trusted_fetch"]["git_tree"] == "1" * 40
    assert descriptor["artifacts"][0]["filename"] == "fixture_dep-2.0-py3-none-any.whl"
    assert descriptor["artifacts"][0]["tags"] == ["py3-none-any"]
    assert (destination / descriptor["manager_lock"]["path"]).is_file()
    assert (destination / "COMPLETE").read_text() == descriptor["content_sha256"] + "\n"


def test_bundle_rejects_combined_files_above_consumer_limit(monkeypatch: Any, tmp_path: Path) -> None:
    module, accepted, _ = _bundle(tmp_path)
    total = sum(path.stat().st_size for path in accepted.rglob("*") if path.is_file())
    limit = total - 1
    assert (accepted / "source.tar.gz").stat().st_size < limit
    assert sum(path.stat().st_size for path in (accepted / "source").rglob("*") if path.is_file()) < limit
    assert sum(path.stat().st_size for path in (accepted / "wheelhouse").iterdir()) < limit
    monkeypatch.setattr(module, "MAX_BUNDLE_BYTES", total, raising=False)
    module.verify_acquisition_bundle(accepted, verifier=_verify)
    monkeypatch.setattr(module, "MAX_BUNDLE_BYTES", limit, raising=False)
    with pytest.raises(ValueError, match="bundle_bytes_exceeded"):
        module.verify_acquisition_bundle(accepted, verifier=_verify)

    request = module.build_acquisition_request(_entry(), "3.13")
    destination = tmp_path / "rejected"
    with pytest.raises(ValueError, match="bundle_bytes_exceeded"):
        module.create_acquisition_bundle(
            request,
            tmp_path / "source.tar.gz",
            artifacts=[_wheel(tmp_path)],
            destination=destination,
            signer=_sign,
            source_verifier=_verify_source,
        )
    assert not destination.exists()


def test_acquisition_rejects_commit_url_filename_hash_and_incompatible_tags(tmp_path: Path) -> None:
    module = api()
    request = module.build_acquisition_request(_entry(), "3.13")
    archive = _archive(tmp_path)
    good = _wheel(tmp_path)
    mutations = [
        {**good, "url": "file:///tmp/fixture.whl"},
        {**good, "url": "https://example.com/fixture.whl"},
        {**good, "filename": "renamed.whl"},
        {**good, "sha256": "0" * 64},
        _wheel(tmp_path, filename="fixture_dep-2.0-cp313-cp313-macosx_14_0_x86_64.whl"),
    ]
    for index, artifact in enumerate(mutations):
        with pytest.raises(ValueError, match="acquisition"):
            module.create_acquisition_bundle(
                request,
                archive,
                artifacts=[artifact],
                destination=tmp_path / f"rejected-{index}",
                signer=_sign,
                source_verifier=_verify_source,
            )

    def wrong_commit(trusted_request: dict[str, Any], archive_sha256: str, tree_sha256: str) -> dict[str, Any]:
        evidence = _verify_source(trusted_request, archive_sha256, tree_sha256)
        evidence["commit"] = "0" * 40
        return evidence

    with pytest.raises(ValueError, match="acquisition"):
        module.create_acquisition_bundle(
            request,
            archive,
            artifacts=[good],
            destination=tmp_path / "wrong-source-evidence",
            signer=_sign,
            source_verifier=wrong_commit,
        )


def test_sdist_is_bound_for_preparation_build_hook_without_execution(tmp_path: Path) -> None:
    module = api()
    request = module.build_acquisition_request(_entry("hatch"), "3.12")
    sdist = tmp_path / "fixture_dep-2.0.tar.gz"
    sdist.write_bytes(b"sdist fixture")
    descriptor = module.create_acquisition_bundle(
        request,
        _archive(tmp_path),
        artifacts=[
            {
                "package": "fixture-dep",
                "version": "2.0",
                "filename": sdist.name,
                "url": f"https://files.pythonhosted.org/packages/aa/{sdist.name}",
                "path": sdist,
                "sha256": hashlib.sha256(sdist.read_bytes()).hexdigest(),
            }
        ],
        destination=tmp_path / "sdist-bundle",
        signer=_sign,
        source_verifier=_verify_source,
    )
    assert descriptor["artifacts"][0]["kind"] == "sdist"
    assert descriptor["artifacts"][0]["build_hook_required"] is True
    assert descriptor["acquisition_executed_project_code"] is False


def test_compatible_arm64_abi3_wheel_is_admitted(tmp_path: Path) -> None:
    module = api()
    request = module.build_acquisition_request(_entry(), "3.13")
    wheel = _wheel(tmp_path, filename="fixture_dep-2.0-cp311-abi3-macosx_14_0_arm64.whl")
    descriptor = module.create_acquisition_bundle(
        request,
        _archive(tmp_path),
        artifacts=[wheel],
        destination=tmp_path / "abi3-bundle",
        signer=_sign,
        source_verifier=_verify_source,
    )
    assert descriptor["artifacts"][0]["tags"] == ["cp311-abi3-macosx_14_0_arm64"]
    assert descriptor["artifacts"][0]["build_hook_required"] is False


def test_changed_bytes_signature_and_partial_cache_are_rejected(tmp_path: Path) -> None:
    module, destination, descriptor = _bundle(tmp_path)
    wheel = destination / "wheelhouse" / descriptor["artifacts"][0]["filename"]
    wheel.write_bytes(b"substituted")
    with pytest.raises(ValueError, match="acquisition"):
        module.verify_acquisition_bundle(destination, verifier=_verify)

    module, destination, _ = _bundle(tmp_path / "extra")
    (destination / "wheelhouse/unrecorded.whl").write_bytes(b"not admitted")
    with pytest.raises(ValueError, match="acquisition"):
        module.verify_acquisition_bundle(destination, verifier=_verify)

    module, destination, descriptor = _bundle(tmp_path / "mode")
    (destination / "wheelhouse" / descriptor["artifacts"][0]["filename"]).chmod(0o644)
    with pytest.raises(ValueError, match="acquisition"):
        module.verify_acquisition_bundle(destination, verifier=_verify)

    module, destination, _ = _bundle(tmp_path / "second")
    (destination / "COMPLETE").unlink()
    with pytest.raises(ValueError, match="acquisition"):
        module.verify_acquisition_bundle(destination, verifier=_verify)


def test_atomic_offline_cache_reuse_rejects_interrupted_or_substituted_content(tmp_path: Path) -> None:
    module, staged, descriptor = _bundle(tmp_path)
    cache = tmp_path / "cache"
    installed = module.install_acquisition_bundle(staged, cache, verifier=_verify)
    assert installed.name == descriptor["content_sha256"]
    assert module.open_offline_bundle(cache, descriptor["content_sha256"], verifier=_verify) == installed

    partial = cache / (descriptor["content_sha256"] + ".partial")
    partial.mkdir()
    assert module.open_offline_bundle(cache, descriptor["content_sha256"], verifier=_verify) == installed

    (installed / "descriptor.json").write_text("{}")
    with pytest.raises(ValueError, match="acquisition"):
        module.open_offline_bundle(cache, descriptor["content_sha256"], verifier=_verify)


def test_source_archive_rejects_links_and_path_traversal(tmp_path: Path) -> None:
    module = api()
    request = module.build_acquisition_request(_entry(), "3.13")
    for index, name in enumerate(("../escape", "project/link")):
        archive = tmp_path / f"unsafe-{index}.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            details = tarfile.TarInfo(name)
            if index:
                details.type = tarfile.SYMTYPE
                details.linkname = "/tmp/escape"
            else:
                details.size = 1
                bundle.addfile(details, io.BytesIO(b"x"))
                continue
            bundle.addfile(details)
        with pytest.raises(ValueError, match="acquisition"):
            module.create_acquisition_bundle(
                request,
                archive,
                artifacts=[_wheel(tmp_path, filename=f"fixture_dep-2.{index}-py3-none-any.whl")],
                destination=tmp_path / f"unsafe-output-{index}",
                signer=_sign,
                source_verifier=_verify_source,
            )


def test_source_extraction_streams_to_nofollow_files_and_preflights_member_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = api()
    archive = _archive(tmp_path)
    original_open = module.os.open
    flags = []

    def observed_open(path: Path, selected: int, mode: int) -> int:
        flags.append(selected)
        return original_open(path, selected, mode)

    monkeypatch.setattr(module.os, "open", observed_open)
    inventory = module._extract_source(archive, tmp_path / "streamed")
    assert inventory
    assert flags and all(selected & module.os.O_EXCL for selected in flags)
    if hasattr(module.os, "O_NOFOLLOW"):
        assert all(selected & module.os.O_NOFOLLOW for selected in flags)

    class HugeMember:
        name = "project/huge.bin"
        size = module.MAX_SOURCE_BYTES + 1
        mode = 0o644

        @staticmethod
        def issym() -> bool:
            return False

        @staticmethod
        def islnk() -> bool:
            return False

        @staticmethod
        def isfile() -> bool:
            return True

        @staticmethod
        def isdir() -> bool:
            return False

    class HugeBundle:
        def __enter__(self) -> HugeBundle:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        @staticmethod
        def getmembers() -> list[HugeMember]:
            return [HugeMember()]

        @staticmethod
        def extractfile(_member: HugeMember) -> None:
            raise AssertionError("oversized member must be rejected before allocation or extraction")

    monkeypatch.setattr(module.tarfile, "open", lambda *_args, **_kwargs: HugeBundle())
    with pytest.raises(ValueError, match="source_archive_too_large"):
        module._extract_source(archive, tmp_path / "oversized")
