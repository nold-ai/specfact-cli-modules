from __future__ import annotations

import base64
import hashlib
import io
import json
import shutil
import struct
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from scripts import build_macos_managed_git as git_builder, build_macos_native_capsule as builder
from specfact_code_review.run.native_capsule import acquire_native_capsule


ANALYZER_VERSIONS = {
    "ai-bloat-ast": "module-release-bound",
    "ast-clean-code": "module-release-bound",
    "basedpyright": "1.39.10",
    "contracts": "crosshair-tool-0.0.109+icontract-2.7.1",
    "pylint": "4.0.7",
    "radon": "6.0.1",
    "ruff": "0.15.12",
    "semgrep-bugs": "1.175.0",
    "semgrep-clean": "1.175.0",
    "targeted-pytest-coverage": "pytest-9.0.3+pytest-cov-7.1.0+coverage-7.15.4",
}


def _macho(*, cpu: int = 0x0100000C, subtype: int = 0, load: str = "/usr/lib/libSystem.B.dylib") -> bytes:
    encoded = load.encode() + b"\0"
    size = (24 + len(encoded) + 7) & ~7
    command = bytearray(size)
    struct.pack_into("<III", command, 0, 0xC, size, 24)
    command[24 : 24 + len(encoded)] = encoded
    return struct.pack("<IIIIIIII", 0xFEEDFACF, cpu, subtype, 2, 1, size, 0, 0) + command


@pytest.fixture
def build_case(tmp_path: Path):
    root = tmp_path / "runtime"
    (root / "bin").mkdir(parents=True)
    (root / "provenance").mkdir()
    (root / "licenses").mkdir()
    (root / "bin/broker").write_bytes(_macho())
    (root / "bin/broker").chmod(0o755)
    (root / "provenance/runtime.json").write_text('{"source":"fixture"}\n')
    (root / "licenses/runtime.txt").write_text("fixture license\n")
    key = ed25519.Ed25519PrivateKey.generate()
    closure = {
        "broker-v1": ["bin/broker"],
        "licenses-v1": ["licenses/runtime.txt"],
        "provenance-v1": ["provenance/runtime.json"],
    }
    signing = {
        "format": "mach-o",
        "mode": "adhoc",
        "identifier": "ai.nold.specfact.broker",
        "cdhash": "a" * 40,
        "hardened_runtime": True,
    }

    def invoke(**overrides):
        options = {
            "runtime_root": root,
            "output_dir": tmp_path / "out",
            "closure": closure,
            "environment_id": "darwin-arm64-cp312",
            "backend": "managed-v1",
            "policy": "deny-v1",
            "analyzer_versions": ANALYZER_VERSIONS,
            "private_key": key,
            "signature_inspector": lambda _path: dict(signing),
            "entitlements_inspector": lambda _path: {"com.apple.security.cs.allow-jit": True},
        }
        options.update(overrides)
        return builder.build_native_capsule(**options)

    return root, key, closure, signing, invoke


def test_build_is_deterministic_and_manifest_is_consumer_compatible(build_case, tmp_path: Path) -> None:
    _root, _key, _closure, _signing, invoke = build_case
    first = invoke()
    second = invoke(output_dir=tmp_path / "other")

    assert first.archive.read_bytes() == second.archive.read_bytes()
    assert first.manifest.read_bytes() == second.manifest.read_bytes()
    assert first.signature is not None and second.signature is not None
    assert first.signature.read_bytes() == second.signature.read_bytes()


def test_builder_manifest_and_signing_metadata_match_serialized_archive(build_case) -> None:
    _root, _key, _closure, signing, invoke = build_case
    first = invoke()
    document = json.loads(first.manifest.read_bytes())
    expected_archive_size = (
        sum(512 + ((record["size"] + 511) // 512) * 512 for record in document["files"].values()) + 1024
    )
    assert document["archive"]["size"] == expected_archive_size
    assert document["schema"] == "specfact-native-capsule-v1"
    assert document["analyzer_versions"] == ANALYZER_VERSIONS
    assert document["native_signatures"] == {"bin/broker": signing}
    assert "metadata/native-signing.json" in document["files"]
    with tarfile.open(fileobj=io.BytesIO(first.archive.read_bytes()), mode="r:") as archive:
        signing_member = archive.extractfile("metadata/native-signing.json")
        assert signing_member is not None
        signing_detail = json.load(signing_member)
    assert signing_detail == {
        "schema": "specfact-native-signing-v1",
        "images": {
            "bin/broker": {
                "signature": signing,
                "entitlements": {"com.apple.security.cs.allow-jit": True},
            }
        },
    }
    assert json.loads(first.summary.read_text()) == {
        "archive_sha256": document["archive"]["sha256"],
        "archive_size": document["archive"]["size"],
        "environment_id": "darwin-arm64-cp312",
        "file_count": 4,
        "manifest_sha256": builder.sha256(first.manifest.read_bytes()),
        "native_image_count": 1,
        "production_eligible": False,
        "publication": "candidate-only",
        "signing_mode": "adhoc",
    }


def test_builder_signature_and_manifest_roundtrip_through_native_consumer(build_case, tmp_path: Path) -> None:
    _root, key, _closure, signing, invoke = build_case
    first = invoke()
    assert first.signature is not None
    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with acquire_native_capsule(
        tmp_path / "cache",
        first.manifest.read_bytes(),
        first.signature.read_text() if first.signature else "",
        public_key,
        environment_id="darwin-arm64-cp312",
        backend="managed-v1",
        policy="deny-v1",
        reader=lambda: io.BytesIO(first.archive.read_bytes()),
        signature_inspector=lambda _path: signing,
    ) as lease:
        assert lease.evidence["native_signing_verified"] is True
        assert lease.analyzer_versions == ANALYZER_VERSIONS


def test_output_directory_symlink_is_rejected_without_writing(build_case, tmp_path: Path) -> None:
    _root, _key, _closure, _signing, invoke = build_case
    target = tmp_path / "other-output"
    target.mkdir()
    target.joinpath("sentinel").write_bytes(b"unchanged")
    link = tmp_path / "linked-output"
    link.symlink_to(target, target_is_directory=True)

    with pytest.raises(ValueError, match="ordinary output directory"):
        invoke(output_dir=link)

    assert sorted(path.name for path in target.iterdir()) == ["sentinel"]
    assert (target / "sentinel").read_bytes() == b"unchanged"


@pytest.mark.parametrize("name", ["capsule.tar", "manifest.json", "manifest.sig", "summary.json"])
@pytest.mark.parametrize("collision", ["symlink", "regular"])
def test_existing_output_name_is_rejected_without_writing_or_partial_files(
    build_case, tmp_path: Path, name: str, collision: str
) -> None:
    _root, _key, _closure, _signing, invoke = build_case
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    victim = tmp_path / "victim"
    victim.write_bytes(b"unchanged")
    output = output_dir / name
    if collision == "symlink":
        output.symlink_to(victim)
    else:
        output.write_bytes(b"unchanged")

    with pytest.raises(FileExistsError):
        invoke()

    assert victim.read_bytes() == b"unchanged"
    if collision == "symlink":
        assert output.is_symlink()
    else:
        assert output.read_bytes() == b"unchanged"
    assert sorted(path.name for path in output_dir.iterdir()) == [name]


def test_failed_build_removes_its_own_partial_outputs(
    build_case, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _root, _key, _closure, _signing, invoke = build_case
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    monkeypatch.setattr(builder, "MAX_MANIFEST", 100)

    with pytest.raises(builder.SchemaLimitError, match="native_capsule_schema_limit:manifest_bytes"):
        invoke()

    assert list(output_dir.iterdir()) == []


def test_builder_and_consumer_accept_real_python_metadata_names(build_case, tmp_path: Path) -> None:
    root, key, closure, signing, invoke = build_case
    names = (
        "python/lib/python3.12/site-packages/example/__init__.py",
        "python/lib/python3.12/site-packages/example-1.0.dist-info/METADATA",
        "licenses/example/LICENSE.txt",
    )
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name + "\n", encoding="utf-8")
    expanded = {component: list(paths) for component, paths in closure.items()}
    expanded["python-metadata-v1"] = list(names[:2])
    expanded["licenses-v1"].append(names[2])

    built = invoke(closure=expanded)
    document = json.loads(built.manifest.read_bytes())

    assert set(names).issubset(document["files"])
    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with acquire_native_capsule(
        tmp_path / "metadata-cache",
        built.manifest.read_bytes(),
        built.signature.read_text() if built.signature else "",
        public_key,
        environment_id="darwin-arm64-cp312",
        backend="managed-v1",
        policy="deny-v1",
        reader=lambda: io.BytesIO(built.archive.read_bytes()),
        signature_inspector=lambda _path: signing,
    ) as lease:
        assert all((lease.path / name).is_file() for name in names)


@pytest.mark.parametrize("fault", ["missing", "extra", "duplicate", "symlink"])
def test_closure_rejects_missing_extra_duplicate_and_symlink_members(build_case, fault: str) -> None:
    root, _key, closure, _signing, invoke = build_case
    changed = {name: list(paths) for name, paths in closure.items()}
    if fault == "missing":
        changed["broker-v1"] = []
    elif fault == "extra":
        (root / "unexpected.txt").write_text("unsigned")
    elif fault == "duplicate":
        changed["provenance-v1"].append("bin/broker")
    else:
        (root / "licenses/link.txt").symlink_to(root / "licenses/runtime.txt")
        changed["licenses-v1"].append("licenses/link.txt")
    with pytest.raises(ValueError, match=r"closure|symlink|undeclared"):
        invoke(closure=changed)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (_macho(cpu=0x01000007), "architecture_unsupported"),
        (_macho(load="/opt/homebrew/lib/libbad.dylib"), "absolute_load_path"),
        (b"\\x7fELF" + b"\\0" * 64, "mixed|executable_not_macho"),
    ],
)
def test_native_closure_rejects_architecture_rpath_and_mixed_formats(build_case, payload: bytes, message: str) -> None:
    root, _key, _closure, _signing, invoke = build_case
    (root / "bin/broker").write_bytes(payload)
    with pytest.raises(ValueError, match=message):
        invoke()


@pytest.mark.parametrize(
    "signing",
    [
        {"format": "mach-o", "mode": "developer-id", "identifier": "x", "cdhash": "a" * 40, "hardened_runtime": True},
        {"format": "mach-o", "mode": "adhoc", "identifier": "x", "cdhash": "a" * 40, "hardened_runtime": False},
        {
            "format": "mach-o",
            "mode": "adhoc",
            "identifier": "bad identity",
            "cdhash": "a" * 40,
            "hardened_runtime": True,
        },
        {"format": "mach-o", "mode": "adhoc", "identifier": "x", "cdhash": "not-a-digest", "hardened_runtime": True},
    ],
)
def test_signature_must_be_adhoc_hardened_runtime(build_case, signing: dict[str, object]) -> None:
    _root, _key, _closure, _valid, invoke = build_case
    with pytest.raises(ValueError, match="ad-hoc hardened-runtime"):
        invoke(signature_inspector=lambda _path: signing)


def test_native_extension_codesign_identifier_is_admitted(build_case) -> None:
    _root, _key, _closure, signing, invoke = build_case
    extension_signing = {**signing, "identifier": "_cffi_backend.cpython-312-darwin"}

    built = invoke(signature_inspector=lambda _path: extension_signing)

    document = json.loads(built.manifest.read_bytes())
    assert document["native_signatures"]["bin/broker"]["identifier"] == ("_cffi_backend.cpython-312-darwin")


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute", "Upper/file", "bad space/file"])
def test_unsafe_paths_are_rejected(build_case, unsafe: str) -> None:
    _root, _key, closure, _signing, invoke = build_case
    changed = {name: list(paths) for name, paths in closure.items()}
    changed["broker-v1"] = [unsafe]
    with pytest.raises(ValueError, match=r"path|closure"):
        invoke(closure=changed)


@pytest.mark.parametrize("name", [".semgrep", "z3++.h", "z3_solver-5.1.0.0+specfact.1.dist-info"])
def test_real_python_package_path_components_are_admitted(name: str) -> None:
    builder._safe_name(f"python/site-packages/{name}", label="payload")


def test_generated_signing_component_name_cannot_replace_input_members(build_case) -> None:
    _root, _key, closure, _signing, invoke = build_case
    changed = {name: list(paths) for name, paths in closure.items()}
    changed["native-signing-v1"] = changed.pop("broker-v1")
    with pytest.raises(ValueError, match="generated signing component"):
        invoke(closure=changed)


def test_current_consumer_file_limit_is_a_concrete_blocker(build_case, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _key, closure, _signing, invoke = build_case
    monkeypatch.setattr(builder, "MAX_FILES", 4)
    (root / "licenses/second.txt").write_text("second")
    changed = {name: list(paths) for name, paths in closure.items()}
    changed["licenses-v1"].append("licenses/second.txt")
    with pytest.raises(builder.SchemaLimitError, match="native_capsule_schema_limit:file_count"):
        invoke(closure=changed)


def test_builder_accepts_generated_many_file_runtime(build_case, tmp_path: Path) -> None:
    root, _key, closure, _signing, invoke = build_case
    data = root / "data"
    data.mkdir()
    generated = []
    for index in range(1_000):
        name = f"data/item-{index:05d}.dat"
        (root / name).write_bytes(b"x")
        generated.append(name)
    changed = {name: list(paths) for name, paths in closure.items()}
    changed["runtime-v1"] = generated

    result = invoke(closure=changed, output_dir=tmp_path / "many-out")

    document = json.loads(result.manifest.read_bytes())
    assert len(document["files"]) == 1_004
    assert document["archive"]["size"] == result.archive.stat().st_size


def test_builder_streams_ordinary_payload_files_without_read_bytes(build_case, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _key, _closure, _signing, invoke = build_case
    protected = root / "provenance/runtime.json"
    original = Path.read_bytes

    def guarded(path: Path) -> bytes:
        if path == protected:
            raise AssertionError("ordinary payload must be streamed")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    invoke()


def test_unpacked_size_limit_remains_enforced(build_case, monkeypatch: pytest.MonkeyPatch) -> None:
    root, _key, _closure, _signing, invoke = build_case
    monkeypatch.setattr(builder, "MAX_UNPACKED_BYTES", 512)
    (root / "provenance/runtime.json").write_bytes(b"p" * 513)
    with pytest.raises(builder.SchemaLimitError, match="native_capsule_schema_limit:payload_bytes"):
        invoke()


def test_archive_size_limit_remains_enforced(build_case, monkeypatch: pytest.MonkeyPatch) -> None:
    _root, _key, _closure, _signing, invoke = build_case
    monkeypatch.setattr(builder, "MAX_ARCHIVE_BYTES", 1_000)
    with pytest.raises(builder.SchemaLimitError, match="native_capsule_schema_limit:archive_bytes"):
        invoke()


def test_manifest_limit_is_checked_after_canonical_encoding(build_case, monkeypatch: pytest.MonkeyPatch) -> None:
    _root, _key, _closure, _signing, invoke = build_case
    monkeypatch.setattr(builder, "MAX_MANIFEST", 100)
    with pytest.raises(builder.SchemaLimitError, match="native_capsule_schema_limit:manifest_bytes"):
        invoke()


def test_signature_is_base64_and_matches_canonical_manifest(build_case) -> None:
    _root, key, _closure, _signing, invoke = build_case
    result = invoke()
    assert result.signature is not None
    key.public_key().verify(base64.b64decode(result.signature.read_text()), result.manifest.read_bytes())


def test_builder_cli_imports_repository_package_without_pytest_path_bootstrap() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_macos_native_capsule.py", "--help"],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "--runtime-root" in result.stdout


@pytest.fixture
def managed_git_case(tmp_path, monkeypatch):
    root = tmp_path / "git-artifact"
    root.mkdir()
    source = b"fixture official source archive"
    source_digest = hashlib.sha256(source).hexdigest()
    monkeypatch.setattr(git_builder, "ARCHIVE_SHA256", source_digest)
    requirement = 'cdhash H"' + "b" * 40 + '"'
    data = {
        "bin/git": _macho(),
        "git.requirement": (requirement + "\n").encode(),
        "licenses/Git-COPYING": b"Git GPL license",
        "licenses/sha1dc-LICENSE.txt": b"sha1dc license",
        "licenses/reftable-LICENSE": b"reftable license",
        "source/git-2.54.0.tar.xz": source,
        "build.log": b"private build path /private/tmp/maintainer-input\n",
    }
    for name, contents in data.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
        path.chmod(0o555 if name == "bin/git" else 0o444)
    signature = {
        "format": "mach-o",
        "mode": "adhoc",
        "identifier": git_builder.SIGNING_IDENTIFIER,
        "cdhash": "b" * 40,
        "hardened_runtime": True,
    }
    provenance = {
        "schema": "specfact-managed-git-build-v1",
        "maintainer_only": True,
        "upstream": {
            "version": git_builder.VERSION,
            "commit": git_builder.UPSTREAM_COMMIT,
            "archive_url": git_builder.ARCHIVE_URL,
            "archive_sha256": source_digest,
            "checksum_url": git_builder.CHECKSUM_URL,
        },
        "signing": {
            "mode": "adhoc",
            "identifier": git_builder.SIGNING_IDENTIFIER,
            "cdhash": "b" * 40,
            "requirement": requirement,
        },
        "dependencies": ["/usr/lib/libSystem.B.dylib"],
        "toolchain": {"compiler_version": "fixture clang"},
        "build": {"command": ["make", "git"], "environment": {"HOME": "/private/tmp/input", "PATH": "/usr/bin"}},
        "inventory": {name: hashlib.sha256(contents).hexdigest() for name, contents in data.items()},
    }
    (root / "provenance.json").write_text(json.dumps(provenance))
    (root / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(root).as_posix()}\n"
            for p in sorted(root.rglob("*"))
            if p.is_file()
        )
    )
    (root / "provenance.json").chmod(0o444)
    (root / "SHA256SUMS").chmod(0o444)
    payload = tmp_path / "payload"
    payload.mkdir()
    return root, payload, signature


def test_managed_git_installer_copies_verified_input_without_raw_logs_or_paths(managed_git_case):
    root, payload, signature = managed_git_case
    receipt = builder.install_managed_git_input(root, payload, signature_inspector=lambda _path: signature)
    assert (payload / "git/bin/git").read_bytes() == (root / "bin/git").read_bytes()
    assert (payload / "git/provenance/git.requirement").read_bytes() == (root / "git.requirement").read_bytes()
    assert (payload / "git/provenance/git-2.54.0.tar.xz").read_bytes() == (
        root / "source/git-2.54.0.tar.xz"
    ).read_bytes()
    assert {p.name for p in (payload / "git/licenses").iterdir()} == {
        "Git-COPYING",
        "sha1dc-LICENSE.txt",
        "reftable-LICENSE",
    }
    assert not list((payload / "git").rglob("build.log"))
    assert "/private/" not in json.dumps(receipt)
    assert receipt["production_eligible"] is False
    assert builder.verify_managed_git_input(payload / "git", signature_inspector=lambda _path: signature) == receipt


@pytest.mark.parametrize("fault", ["image", "requirement", "source", "extra", "writable", "symlink", "signature"])
def test_managed_git_installer_rejects_substituted_inputs_before_writing(managed_git_case, fault):
    root, payload, signature = managed_git_case
    if fault in {"image", "requirement", "source"}:
        path = (
            root / {"image": "bin/git", "requirement": "git.requirement", "source": "source/git-2.54.0.tar.xz"}[fault]
        )
        path.chmod(0o644)
        path.write_bytes(b"changed")
    elif fault == "extra":
        (root / "extra").write_bytes(b"undeclared")
    elif fault == "writable":
        (root / "bin/git").chmod(0o755)
    elif fault == "symlink":
        (root / "bin/git").unlink()
        (root / "bin/git").symlink_to(root / "licenses/Git-COPYING")
    else:
        signature = {**signature, "cdhash": "c" * 40}
    with pytest.raises(ValueError, match=r"Git|git"):
        builder.install_managed_git_input(root, payload, signature_inspector=lambda _path: signature)
    assert not (payload / "git").exists()


def test_managed_git_source_route_calls_reproducible_builder_without_manifest_key(managed_git_case, monkeypatch):
    root, payload, signature = managed_git_case
    output = payload.parent / "fresh-git-build"
    calls = []

    def build(source, target, *, jobs):
        calls.append((source, target, jobs))
        shutil.copytree(root, target)

    monkeypatch.setattr(git_builder, "build", build)
    builder.prepare_managed_git_input(
        payload_root=payload,
        source_archive=root / "source/git-2.54.0.tar.xz",
        git_build_output=output,
        jobs=2,
        signature_inspector=lambda _path: signature,
    )
    assert calls == [(root / "source/git-2.54.0.tar.xz", output, 2)]
    assert (payload / "git/bin/git").is_file()


def test_managed_git_payload_tamper_and_duplicate_install_fail_closed(managed_git_case):
    root, payload, signature = managed_git_case

    def inspector(_path):
        return signature

    builder.install_managed_git_input(root, payload, signature_inspector=inspector)
    with pytest.raises(ValueError, match="exist"):
        builder.install_managed_git_input(root, payload, signature_inspector=inspector)
    binary = payload / "git/bin/git"
    binary.chmod(0o755)
    with pytest.raises(ValueError, match=r"Git|git"):
        builder.verify_managed_git_input(payload / "git", signature_inspector=inspector)


def test_managed_git_prepare_cli_is_key_free(monkeypatch, managed_git_case, capsys):
    root, payload, signature = managed_git_case
    original = builder.prepare_managed_git_input
    monkeypatch.setattr(
        builder,
        "prepare_managed_git_input",
        lambda **options: original(**options, signature_inspector=lambda _path: signature),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_macos_native_capsule.py",
            "prepare-managed-git",
            "--git-artifact-root",
            str(root),
            "--payload-root",
            str(payload),
        ],
    )
    assert builder.main() == 0
    assert json.loads(capsys.readouterr().out)["production_eligible"] is False
    assert not list(payload.rglob("manifest.sig"))


@pytest.fixture
def git_build_case(build_case, managed_git_case):
    root, _key, closure, broker_signature, invoke = build_case
    artifact, payload, git_signature = managed_git_case
    receipt = builder.install_managed_git_input(artifact, payload, signature_inspector=lambda _path: git_signature)
    runtime_files = {"bin/git": "tools/git", "provenance/input.json": "provenance/managed-git/input.json"}
    for name in receipt["files"]:
        if name.startswith("licenses/"):
            runtime_files[name] = "licenses/managed-git/" + name.removeprefix("licenses/")
        elif name.startswith("provenance/"):
            runtime_files[name] = "provenance/managed-git/" + name.removeprefix("provenance/")
    for name, target in runtime_files.items():
        path = root / target
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(payload / "git" / name, path)
        path.chmod(0o555 if target == "tools/git" else 0o444)
        closure.setdefault("managed-git-v1", []).append(target)
    (root / "bin/broker").rename(root / "bin/specfact-native-broker")
    closure["broker-v1"] = ["bin/specfact-native-broker"]
    (root / "bin/specfact-native-broker").write_bytes(_macho() + receipt["signing"]["requirement"].encode() + b"\0")
    metadata = {
        "broker_designated_requirement": 'cdhash H"' + "a" * 40 + '"',
        "managed_tool_requirements": {"tools/git": receipt["signing"]["requirement"]},
    }
    (root / "provenance/native-component.json").write_text(json.dumps(metadata))
    closure["provenance-v1"].append("provenance/native-component.json")

    def inspector(path):
        return git_signature if path.name == "git" else broker_signature

    return root, receipt, lambda **options: invoke(signature_inspector=inspector, **options)


def test_managed_git_capsule_manifest_carries_exact_identity_and_receipt(git_build_case):
    _root, receipt, invoke = git_build_case
    manifest = json.loads(invoke().manifest.read_bytes())
    assert manifest["native_signatures"]["tools/git"]["identifier"] == git_builder.SIGNING_IDENTIFIER
    assert manifest["files"]["tools/git"]["sha256"] == receipt["files"]["bin/git"]["sha256"]
    assert "provenance/managed-git/input.json" in manifest["files"]


@pytest.mark.parametrize("fault", ["broker-binding", "broker-identity", "receipt", "requirement", "source", "extra"])
def test_managed_git_packer_checks_binding_before_any_output_or_signing(git_build_case, monkeypatch, fault):
    root, _receipt, invoke = git_build_case
    if fault == "broker-binding":
        (root / "bin/specfact-native-broker").write_bytes(_macho())
    elif fault == "broker-identity":
        path = root / "provenance/native-component.json"
        metadata = json.loads(path.read_bytes())
        metadata["broker_designated_requirement"] = 'cdhash H"' + "c" * 40 + '"'
        path.write_text(json.dumps(metadata))
    else:
        name = {
            "receipt": "input.json",
            "requirement": "git.requirement",
            "source": "git-2.54.0.tar.xz",
            "extra": "undeclared",
        }[fault]
        path = root / "provenance/managed-git" / name
        if path.exists():
            path.chmod(0o644)
        path.write_bytes(b"{}")
        path.chmod(0o444)
    monkeypatch.setattr(builder, "_sign", lambda *_args: pytest.fail("Git preflight reached manifest signing"))
    with pytest.raises(ValueError, match=r"Git|git|broker|undeclared"):
        invoke()
    assert not (root.parent / "out").exists()


def test_unsigned_build_preserves_final_bytes_without_signer(build_case, tmp_path: Path, monkeypatch) -> None:
    _root, _key, _closure, _signing, invoke = build_case
    signed = invoke()

    def forbidden_sign(*args):
        pytest.fail("unsigned build invoked a manifest signer")

    monkeypatch.setattr(builder, "_sign", forbidden_sign)
    unsigned = invoke(output_dir=tmp_path / "unsigned", private_key=None)
    assert unsigned.archive.read_bytes() == signed.archive.read_bytes()
    assert unsigned.manifest.read_bytes() == signed.manifest.read_bytes()
    assert unsigned.signature is None
    assert not (tmp_path / "unsigned/manifest.sig").exists()
    summary = json.loads(unsigned.summary.read_bytes())
    assert summary["manifest_authenticated"] is False
    assert summary["production_eligible"] is False


def test_unsigned_build_still_rejects_invalid_native_signature(build_case, tmp_path: Path) -> None:
    _root, _key, _closure, _signing, invoke = build_case
    with pytest.raises(ValueError, match="ad-hoc hardened-runtime"):
        invoke(private_key=None, signature_inspector=lambda path: {})
    assert not (tmp_path / "out/capsule.tar").exists()
