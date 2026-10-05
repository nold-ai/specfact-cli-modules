from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import BinaryIO

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from specfact_code_review.run import native_capsule


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


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _exact_ustar(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as output:
        for name, data in files.items():
            member = tarfile.TarInfo(name)
            member.mode = 0o500 if name.startswith("bin/") else 0o400
            member.size = len(data)
            member.mtime = 0
            output.addfile(member, io.BytesIO(data))
    exact_size = sum(512 + ((len(data) + 511) // 512) * 512 for data in files.values()) + 1024
    return stream.getvalue()[:exact_size]


def _rechecksum_first_header(archive: bytearray) -> None:
    archive[148:156] = b"        "
    checksum = sum(archive[:512])
    archive[148:156] = f"{checksum:06o}\0 ".encode("ascii")


@pytest.fixture
def capsule_case(tmp_path: Path):
    class Case:
        key = ed25519.Ed25519PrivateKey.generate()
        files = {"bin/broker": b"fixture Mach-O broker", "lib/runtime.dat": b"runtime data"}
        signing = {
            "format": "mach-o",
            "mode": "adhoc",
            "identifier": "ai.nold.specfact.broker",
            "cdhash": "a" * 40,
            "hardened_runtime": True,
        }
        cache_root = tmp_path / "cache"

        def build(self) -> None:
            self.archive = _exact_ustar(self.files)
            closure = {
                "broker-v1": ["bin/broker"],
                "runtime-v1": sorted(set(self.files) - {"bin/broker"}),
            }
            self.document = {
                "schema": "specfact-native-capsule-v1",
                "os": "darwin",
                "architecture": "arm64",
                "environment_id": "darwin-arm64-cp312",
                "abi": "cp312",
                "backend": "managed-v1",
                "policy": "deny-v1",
                "analyzer_versions": dict(ANALYZER_VERSIONS),
                "archive": {"size": len(self.archive), "sha256": _digest(self.archive)},
                "files": {
                    name: {
                        "size": len(data),
                        "mode": 0o500 if name.startswith("bin/") else 0o400,
                        "sha256": _digest(data),
                    }
                    for name, data in self.files.items()
                },
                "closure": closure,
                "closure_sha256": _digest(_canonical(closure)),
                "native_signatures": {"bin/broker": self.signing},
            }

        def invoke(
            self,
            *,
            reader: Callable[[], BinaryIO] | None = None,
            signature_inspector: Callable[[Path], dict[str, object]] | None = None,
            offline: bool = False,
            progress: Callable[[str, int], None] | None = None,
        ) -> native_capsule.NativeCapsuleLease:
            manifest = _canonical(self.document)
            signature = base64.b64encode(self.key.sign(manifest)).decode()
            public_key = self.key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            return native_capsule.acquire_native_capsule(
                self.cache_root,
                manifest,
                signature,
                public_key,
                environment_id="darwin-arm64-cp312",
                backend="managed-v1",
                policy="deny-v1",
                reader=reader or (lambda: io.BytesIO(self.archive)),
                signature_inspector=signature_inspector or (lambda _path: dict(self.signing)),
                offline=offline,
                progress=progress,
            )

    case = Case()
    case.build()
    return case


def test_relative_cache_returns_absolute_cold_and_offline_leases(capsule_case, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    capsule_case.cache_root = Path("relative-cache")
    inspected = []

    def inspect(path):
        assert path.is_absolute()
        inspected.append(path)
        return dict(capsule_case.signing)

    with capsule_case.invoke(signature_inspector=inspect) as lease:
        expected = tmp_path / "relative-cache" / lease.identity
        assert lease.path == expected
    with capsule_case.invoke(offline=True, signature_inspector=inspect) as reused:
        assert reused.path == expected
    assert len(inspected) == 3


def test_cold_install_and_offline_reuse_reverify_payload_and_native_signature(capsule_case) -> None:
    progress: list[tuple[str, int]] = []
    with capsule_case.invoke(progress=lambda phase, count: progress.append((phase, count))) as lease:
        assert os.read(lease.fds["bin/broker"], 100) == capsule_case.files["bin/broker"]
        assert lease.analyzer_versions == ANALYZER_VERSIONS
        identity = lease.identity
        assert lease.evidence["native_signing_verified"] is True
        assert lease.evidence["environment_id"] == "darwin-arm64-cp312"
        assert lease.evidence["production_eligible"] is False
        assert set(lease.fds) == {"bin/broker"}

    with capsule_case.invoke(offline=True, reader=lambda: pytest.fail("offline reuse must not acquire")) as lease:
        assert lease.identity == identity
        assert lease.evidence["native_signing_verified"] is True

    assert {phase for phase, _count in progress} == {"downloading", "verifying", "ready"}


@pytest.mark.parametrize("fault", ["missing", "extra", "malformed"])
def test_manifest_rejects_incomplete_analyzer_version_binding(capsule_case, fault: str) -> None:
    if fault == "missing":
        capsule_case.document["analyzer_versions"].pop("semgrep-clean")
    elif fault == "extra":
        capsule_case.document["analyzer_versions"]["unknown"] = "1.0"
    else:
        capsule_case.document["analyzer_versions"]["semgrep-clean"] = ""

    with pytest.raises(ValueError, match="analyzer version"):
        capsule_case.invoke()


def test_manifest_rejects_signed_darwin_semgrep_version_outside_native_policy(capsule_case) -> None:
    capsule_case.document["analyzer_versions"]["semgrep-clean"] = "1.144.0"
    capsule_case.document["analyzer_versions"]["semgrep-bugs"] = "1.144.0"

    with pytest.raises(ValueError, match="native Semgrep version policy"):
        capsule_case.invoke()


def test_archive_progress_is_coarse_and_reports_final_byte_count(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"x" * (5 * native_capsule.CHUNK)
    events: list[tuple[str, int]] = []
    monkeypatch.setattr(native_capsule, "PROGRESS_INTERVAL_BYTES", 2 * native_capsule.CHUNK)
    reader = native_capsule._ArchiveReader(
        io.BytesIO(payload),
        {"size": len(payload), "sha256": _digest(payload)},
        lambda phase, count: events.append((phase, count)),
    )

    assert reader.read_exact(len(payload)) == payload
    reader.finish()

    assert events == [
        ("downloading", 2 * native_capsule.CHUNK),
        ("downloading", 4 * native_capsule.CHUNK),
        ("downloading", 5 * native_capsule.CHUNK),
    ]


def test_manifest_accepts_native_extension_codesign_identifier(capsule_case) -> None:
    capsule_case.signing = {
        **capsule_case.signing,
        "identifier": "_cffi_backend.cpython-312-darwin",
    }
    capsule_case.build()

    with capsule_case.invoke() as lease:
        assert lease.evidence["native_signing_verified"] is True


def test_full_runtime_profile_has_explicit_scalable_bounds() -> None:
    assert native_capsule.MAX_ARCHIVE_BYTES == 4 * 1024**3
    assert native_capsule.MAX_UNPACKED_BYTES == 4 * 1024**3
    assert native_capsule.MAX_FILES == 200_000
    assert native_capsule.MAX_FILE_BYTES == 2 * 1024**3
    assert native_capsule.MAX_MANIFEST == 64 * 1024**2
    assert native_capsule.MAX_PATH_BYTES == 240
    assert native_capsule.MAX_PATH_DEPTH == 32


def test_cold_install_creates_missing_cache_parents_without_following_links(capsule_case, tmp_path: Path) -> None:
    capsule_case.cache_root = tmp_path / "nested" / "code-review" / "capsules"

    with capsule_case.invoke() as lease:
        assert lease.path.parent == capsule_case.cache_root

    assert capsule_case.cache_root.stat().st_mode & 0o777 == 0o700


def test_manifest_signature_is_required_before_reader_is_opened(capsule_case) -> None:
    manifest = _canonical(capsule_case.document)
    public_key = capsule_case.key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with pytest.raises(ValueError, match="signature"):
        native_capsule.acquire_native_capsule(
            capsule_case.cache_root,
            manifest,
            base64.b64encode(b"forged").decode(),
            public_key,
            environment_id="darwin-arm64-cp312",
            backend="managed-v1",
            policy="deny-v1",
            reader=lambda: pytest.fail("unauthenticated metadata must not open the payload reader"),
            signature_inspector=lambda _path: dict(capsule_case.signing),
        )


@pytest.mark.parametrize("fault", ["environment", "payload", "closure", "missing-signing", "extra-signing"])
def test_manifest_rejects_unbound_platform_payload_and_signing_metadata(capsule_case, fault: str) -> None:
    if fault == "environment":
        capsule_case.document["environment_id"] = "darwin-arm64-cp313"
    elif fault == "payload":
        capsule_case.document["files"]["bin/broker"]["sha256"] = "0" * 64
    elif fault == "closure":
        capsule_case.document["closure"] = {"broker-v1": ["bin/broker"]}
        capsule_case.document["closure_sha256"] = _digest(_canonical(capsule_case.document["closure"]))
    elif fault == "missing-signing":
        capsule_case.document["native_signatures"] = {}
    else:
        capsule_case.document["native_signatures"]["lib/runtime.dat"] = dict(capsule_case.signing)

    with pytest.raises(ValueError):
        capsule_case.invoke()


def test_observed_native_signature_must_match_authenticated_record(capsule_case) -> None:
    observed = dict(capsule_case.signing)
    observed["cdhash"] = "b" * 40

    with pytest.raises(ValueError, match="native signature metadata mismatch"):
        capsule_case.invoke(signature_inspector=lambda _path: observed)

    assert not [entry for entry in capsule_case.cache_root.iterdir() if len(entry.name) == 64]


def test_offline_cache_miss_is_actionable_incomplete(capsule_case) -> None:
    with pytest.raises(native_capsule.NativeCapsuleIncompleteError, match="offline cache missing") as caught:
        capsule_case.invoke(offline=True)

    assert caught.value.evidence["status"] == "INCOMPLETE"
    assert caught.value.evidence["environment_id"] == "darwin-arm64-cp312"
    assert caught.value.evidence["production_eligible"] is False


def test_warm_cache_corruption_fails_closed(capsule_case) -> None:
    with capsule_case.invoke() as lease:
        broker = lease.path / "bin/broker"
    broker.chmod(0o700)
    broker.write_bytes(b"corrupt")
    broker.chmod(0o500)

    with pytest.raises(ValueError):
        capsule_case.invoke(offline=True)


def test_interrupted_install_never_publishes_partial_identity(capsule_case) -> None:
    class Interrupted(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        capsule_case.invoke(reader=lambda: Interrupted(capsule_case.archive))

    published = [entry for entry in capsule_case.cache_root.iterdir() if len(entry.name) == 64]
    assert published == []


def test_stream_reader_never_receives_unbounded_or_oversized_read(capsule_case) -> None:
    requests: list[int] = []

    class GuardedReader(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            assert size is not None and 0 <= size <= native_capsule.CHUNK
            requests.append(size)
            return super().read(size)

    with capsule_case.invoke(reader=lambda: GuardedReader(capsule_case.archive)):
        pass

    assert requests and max(requests) <= 64 * 1024


def test_stream_reader_accepts_short_bounded_chunks(capsule_case) -> None:
    class ChunkedReader(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            assert size is not None and size >= 0
            return super().read(min(size, 7))

    with capsule_case.invoke(reader=lambda: ChunkedReader(capsule_case.archive)):
        pass


def test_streaming_accepts_generated_many_file_fixture(capsule_case) -> None:
    capsule_case.files = {
        "bin/broker": b"fixture Mach-O broker",
        **{f"lib/items/item-{index:05d}.dat": b"x" for index in range(1_000)},
    }
    capsule_case.build()

    with capsule_case.invoke() as lease:
        assert set(lease.fds) == {"bin/broker"}
        assert (lease.path / "lib/items/item-00999.dat").read_bytes() == b"x"


def test_streaming_rejects_trailing_zero_block_even_when_signed(capsule_case) -> None:
    capsule_case.archive += b"\0" * 512
    capsule_case.document["archive"] = {
        "size": len(capsule_case.archive),
        "sha256": _digest(capsule_case.archive),
    }

    with pytest.raises(ValueError, match=r"trailing|end blocks"):
        capsule_case.invoke()


@pytest.mark.parametrize(
    ("fault", "typeflag"),
    [("pax", b"x"), ("sparse", b"S"), ("symlink", b"2"), ("device", b"3")],
)
def test_streaming_rejects_nonregular_ustar_records(capsule_case, fault: str, typeflag: bytes) -> None:
    assert fault in {"pax", "sparse", "symlink", "device"}
    archive = bytearray(capsule_case.archive)
    archive[156:157] = typeflag
    _rechecksum_first_header(archive)
    capsule_case.archive = bytes(archive)
    capsule_case.document["archive"]["sha256"] = _digest(capsule_case.archive)

    with pytest.raises(ValueError, match="regular"):
        capsule_case.invoke()


def test_streaming_rejects_gnu_tar_header(capsule_case) -> None:
    archive = bytearray(capsule_case.archive)
    archive[257:265] = b"ustar  \0"
    _rechecksum_first_header(archive)
    capsule_case.archive = bytes(archive)
    capsule_case.document["archive"]["sha256"] = _digest(capsule_case.archive)

    with pytest.raises(ValueError, match="magic"):
        capsule_case.invoke()


def test_disk_space_preflight_happens_before_reader_open(capsule_case, monkeypatch: pytest.MonkeyPatch) -> None:
    opened = False

    def reader() -> BinaryIO:
        nonlocal opened
        opened = True
        return io.BytesIO(capsule_case.archive)

    monkeypatch.setattr(native_capsule, "_available_disk_bytes", lambda _fd: 0, raising=False)
    with pytest.raises(ValueError, match="disk space"):
        capsule_case.invoke(reader=reader)
    assert opened is False


def test_concurrent_cold_install_publishes_one_verified_identity(capsule_case) -> None:
    reader_calls: list[int] = []

    def reader() -> BinaryIO:
        reader_calls.append(1)
        return io.BytesIO(capsule_case.archive)

    def install(_index: int) -> str:
        with capsule_case.invoke(reader=reader) as lease:
            return lease.identity

    with ThreadPoolExecutor(max_workers=4) as pool:
        identities = list(pool.map(install, range(8)))

    assert len(set(identities)) == 1
    assert reader_calls == [1]


@pytest.mark.skipif(sys.platform != "darwin", reason="requires the macOS code-signing verifier")
def test_default_native_signature_inspector_reads_adhoc_hardened_runtime_metadata(tmp_path: Path) -> None:
    fixture = tmp_path / "signed-fixture"
    shutil.copyfile("/usr/bin/true", fixture)
    fixture.chmod(0o700)
    subprocess.run(
        ["/usr/bin/codesign", "--force", "--sign", "-", "--options", "runtime", str(fixture)],
        check=True,
        capture_output=True,
        text=True,
    )

    observed = native_capsule.inspect_native_signature(fixture)

    assert observed["format"] == "mach-o"
    assert observed["mode"] == "adhoc"
    assert observed["hardened_runtime"] is True
    assert isinstance(observed["identifier"], str) and observed["identifier"]
    assert isinstance(observed["cdhash"], str) and len(observed["cdhash"]) in {40, 64}
