"""Locked HTTPS Git acquisition authenticates tree bytes before hook execution."""

import hashlib
import io
import tarfile

import pytest

from specfact_code_review.run import native_project_source as source
from specfact_code_review.run.runtime_models import ProjectRuntimeError


DECLARATION = {
    "schema": "native-locked-git-v1",
    "name": "poetry-core",
    "version": "2.5.0.dev0",
    "url": "https://github.com/python-poetry/poetry-core.git",
    "reference": "HEAD",
    "commit": "b9663e42c808543377ae523611c4cfad68016f30",
    "subdirectory": "",
}


@pytest.mark.parametrize(
    "change",
    [
        {"url": "http://github.com/o/r.git"},
        {"url": "https://user:pass@github.com/o/r.git"},
        {"commit": "HEAD"},
        {"subdirectory": "../host"},
        {"extra": True},
    ],
)
def test_locked_declaration_is_closed_and_exact(change):
    with pytest.raises(ProjectRuntimeError, match="source_request_invalid"):
        source.validate_declaration({**DECLARATION, **change})


def tree_fixture():
    content = b"VALUE=1\n"
    blob = source.git_hash("blob", content)
    subtree = source.git_hash("tree", b"100644 module.py\0" + bytes.fromhex(blob))
    root = source.git_hash("tree", b"40000 src\0" + bytes.fromhex(subtree))
    entries = [
        {"path": "src", "mode": "040000", "type": "tree", "sha": subtree},
        {"path": "src/module.py", "mode": "100644", "type": "blob", "sha": blob, "size": len(content)},
    ]
    return content, root, entries


def test_tree_verification_reconstructs_git_identity(tmp_path):
    content, root, entries = tree_fixture()
    (tmp_path / "src").mkdir()
    (tmp_path / "src/module.py").write_bytes(content)
    inventory = source.verify_tree(tmp_path, root, entries)
    assert inventory["src/module.py"]["sha256"] == hashlib.sha256(content).hexdigest()
    (tmp_path / "src/module.py").write_bytes(b"changed\n")
    with pytest.raises(ProjectRuntimeError, match="source_tree_mismatch"):
        source.verify_tree(tmp_path, root, entries)


@pytest.mark.parametrize("mode,kind", [("120000", "blob"), ("160000", "commit")])
def test_tree_cannot_admit_links_or_submodules(tmp_path, mode, kind):
    with pytest.raises(ProjectRuntimeError, match="source_tree_invalid"):
        source.verify_tree(tmp_path, "1" * 40, [{"path": "escape", "mode": mode, "type": kind, "sha": "2" * 40}])


def test_tree_rejects_unexpected_files_and_lfs(tmp_path):
    content, root, entries = tree_fixture()
    (tmp_path / "src").mkdir()
    (tmp_path / "src/module.py").write_bytes(content)
    (tmp_path / "unexpected").write_text("extra")
    with pytest.raises(ProjectRuntimeError, match="source_tree_mismatch"):
        source.verify_tree(tmp_path, root, entries)
    (tmp_path / "unexpected").unlink()
    pointer = b"version https://git-lfs.github.com/spec/v1\noid sha256:123\n"
    (tmp_path / "src/module.py").write_bytes(pointer)
    entries[1]["sha"] = source.git_hash("blob", pointer)
    with pytest.raises(ProjectRuntimeError, match="source_lfs_unsupported"):
        source.verify_tree(tmp_path, root, entries)


def test_archive_paths_do_not_escape(tmp_path):
    archive = tmp_path / "source.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        info = tarfile.TarInfo("repo/../../outside")
        info.size = 1
        stream.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(ProjectRuntimeError, match="source_archive_invalid"):
        source.extract_archive(archive, tmp_path / "tree")
    assert not (tmp_path / "outside").exists()


def test_acquisition_requires_exact_authenticated_commit(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(
        source, "_fetch", lambda *args: json.dumps({"sha": "0" * 40, "tree": {"sha": "1" * 40}}).encode()
    )
    with pytest.raises(ProjectRuntimeError, match="source_commit_mismatch"):
        source.acquire(DECLARATION, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_source_wheel_binding_rejects_forged_metadata_and_bytes(tmp_path):
    import zipfile
    from types import SimpleNamespace

    declaration = {**DECLARATION, "version": "2.4.1"}
    wheel = tmp_path / "poetry_core-2.4.1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "poetry_core-2.4.1.dist-info/METADATA", "Metadata-Version: 2.1\nName: other-package\nVersion: 2.4.1\n"
        )
        archive.writestr(
            "poetry_core-2.4.1.dist-info/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        )
    receipt = {"tree": "1" * 40, "inventory": {}}
    with pytest.raises(ProjectRuntimeError, match="source_wheel_invalid"):
        source.bind_wheel(wheel, declaration, receipt)
    package = SimpleNamespace(
        name="poetry-core",
        version="2.4.1",
        source_type="git",
        source_url=declaration["url"],
        source_reference="HEAD",
        source_resolved_reference=declaration["commit"],
        source_subdirectory=None,
    )
    binding = {
        "schema": source.BINDING_SCHEMA,
        "declaration": declaration,
        "tree": "1" * 40,
        "inventory_sha256": "2" * 64,
        "wheel": wheel.name,
        "sha256": "0" * 64,
    }
    with pytest.raises(ProjectRuntimeError, match="binding_invalid"):
        source.bound_wheel(tmp_path, package, [binding])
    package.source_resolved_reference = "0" * 40
    with pytest.raises(ProjectRuntimeError, match="binding_missing"):
        source.bound_wheel(tmp_path, package, [binding])


def test_https_acquisition_uses_explicit_verified_capsule_ca(monkeypatch):
    import ssl
    import urllib.request
    from types import SimpleNamespace

    observed = []

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, limit):
            return b"{}"

        def geturl(self):
            return "https://api.github.com/repos/owner/repo"

    def opener(*handlers):
        observed.extend(handlers)
        return SimpleNamespace(open=lambda *args, **kwargs: Response())

    monkeypatch.setattr(urllib.request, "build_opener", opener)
    assert source._fetch("https://api.github.com/repos/owner/repo", 100) == b"{}"
    https = [handler for handler in observed if isinstance(handler, urllib.request.HTTPSHandler)]
    assert len(https) == 1
    assert https[0]._context.verify_mode == ssl.CERT_REQUIRED
    assert https[0]._context.check_hostname is True
