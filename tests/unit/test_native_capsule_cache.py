"""Concrete acquisition adversarial tests; fixture signatures confer no admission."""

import base64
import hashlib
import importlib.util
import io
import json
import os
import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa


@pytest.fixture
def cache_api():
    scripts = Path(__file__).parents[2] / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location("native_capsule_cache", scripts / "native_capsule_cache.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(scripts))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


@pytest.fixture
def case(tmp_path):
    class Case:
        key: ed25519.Ed25519PrivateKey | rsa.RSAPrivateKey = ed25519.Ed25519PrivateKey.generate()
        files = {"bin/worker": b"fixture executable", "lib/data": b"fixture library"}
        root = tmp_path / "cache"

        def build(self, members=None, tail=b""):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as output:
                for name, data, kind in members or [(n, d, tarfile.REGTYPE) for n, d in self.files.items()]:
                    member = tarfile.TarInfo(name)
                    member.type, member.mode = kind, 0o500
                    member.size = len(data) if kind == tarfile.REGTYPE else 0
                    member.linkname = "bin/worker" if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ""
                    output.addfile(member, io.BytesIO(data))
            self.archive = stream.getvalue() + tail
            closure = {"worker-v1": sorted(self.files)}
            self.document = {
                "schema": "specfact-native-cache-v1",
                "os": "darwin",
                "architecture": "arm64",
                "abi": "3.11",
                "backend": "managed-v1",
                "policy": "deny-v1",
                "archive": {"size": len(self.archive), "sha256": digest(self.archive)},
                "files": {n: {"size": len(d), "mode": 0o500, "sha256": digest(d)} for n, d in self.files.items()},
                "closure": closure,
                "closure_sha256": digest(canonical(closure)),
            }
            return self

        def invoke(self, api, **kwargs):
            payload = canonical(self.document)
            signature = (
                self.key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
                if isinstance(self.key, rsa.RSAPrivateKey)
                else self.key.sign(payload)
            )
            pem = self.key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return api.acquire(
                self.root,
                payload,
                base64.b64encode(signature).decode(),
                pem,
                abi="3.11",
                backend="managed-v1",
                policy="deny-v1",
                reader=kwargs.pop("reader", lambda: io.BytesIO(self.archive)),
                **kwargs,
            )

    return Case().build()


@pytest.mark.parametrize("algorithm", ["ed25519", "rsa"])
def test_cold_and_offline_retained_handles(cache_api, case, algorithm):
    if algorithm == "rsa":
        case.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    progress = []
    with case.invoke(cache_api, progress=lambda phase, count: progress.append((phase, count))) as lease:
        assert os.read(lease.fds["bin/worker"], 100) == case.files["bin/worker"]
        assert lease.evidence["production_eligible"] is False
        identity = lease.identity
    with case.invoke(cache_api, offline=True, reader=lambda: pytest.fail("offline network")) as lease:
        assert lease.identity == identity
    assert {phase for phase, _ in progress} >= {"downloading", "verifying", "ready"}


def test_forgery(cache_api, case):
    with pytest.raises(ValueError, match="signature"):
        cache_api.acquire(
            case.root,
            canonical(case.document),
            base64.b64encode(b"forged").decode(),
            case.key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            ),
            abi="3.11",
            backend="managed-v1",
            policy="deny-v1",
        )
    assert not case.root.exists()


@pytest.mark.parametrize("damage", ["digest", "mode", "symlink", "hardlink", "extra", "parent"])
def test_warm_corruption_rejected(cache_api, case, damage):
    with case.invoke(cache_api) as lease:
        root = lease.path
    target = root / "bin/worker"
    if damage == "digest":
        target.chmod(0o700)
        target.write_bytes(b"corrupt")
        target.chmod(0o500)
    elif damage == "mode":
        target.chmod(0o700)
    elif damage == "symlink":
        target.unlink()
        target.symlink_to(root / "lib/data")
    elif damage == "hardlink":
        os.link(target, case.root.parent / "alias")
    elif damage == "extra":
        (root / "extra").write_bytes(b"extra")
    else:
        (root / "bin").rename(root / "renamed")
        (root / "bin").symlink_to(root / "renamed", target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        case.invoke(cache_api, offline=True)


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape", tarfile.REGTYPE),
        ("Bin/worker", tarfile.REGTYPE),
        ("bin//worker", tarfile.REGTYPE),
        ("bin/worker", tarfile.SYMTYPE),
        ("bin/worker", tarfile.LNKTYPE),
        ("bin/worker", tarfile.CHRTYPE),
        ("bin/worker", tarfile.XHDTYPE),
    ],
)
def test_archive_unsafe_members(cache_api, case, name, kind):
    case.build([(name, b"fixture executable", kind)])
    with pytest.raises(ValueError):
        case.invoke(cache_api)


@pytest.mark.parametrize(
    "fault", ["tail", "duplicate", "payload", "closure", "platform", "abi", "descriptor", "oversize"]
)
def test_signed_but_invalid_artifact(cache_api, case, fault):
    if fault == "tail":
        case.build(tail=b"x" * 512)
    elif fault == "duplicate":
        case.build([(n, d, tarfile.REGTYPE) for n, d in case.files.items()] * 2)
    elif fault == "payload":
        case.build([("bin/worker", b"incorrect", tarfile.REGTYPE)])
    elif fault == "closure":
        case.document["closure"] = {"worker-v1": ["bin/worker"]}
        case.document["closure_sha256"] = digest(canonical(case.document["closure"]))
    elif fault == "platform":
        case.document["os"] = "linux"
    elif fault == "abi":
        case.document["abi"] = "3.14"
    elif fault == "descriptor":
        case.document["archive"]["urls"] = ["https://untrusted"]
    else:
        case.document["archive"]["size"] = 64 * 1024 * 1024 + 1
    with pytest.raises(ValueError):
        case.invoke(cache_api)


def test_interruption_and_retry(cache_api, case):
    class Interrupted(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        case.invoke(cache_api, reader=lambda: Interrupted(case.archive))
    assert not list(case.root.glob("[0-9a-f]" * 64))
    (case.root / ".orphan.partial").mkdir()
    with case.invoke(cache_api):
        pass


def test_concurrent_install_once(cache_api, case):
    calls = []

    def reader():
        calls.append(1)
        return io.BytesIO(case.archive)

    def run(_):
        with case.invoke(cache_api, reader=reader) as lease:
            return lease.identity

    with ThreadPoolExecutor(max_workers=6) as pool:
        identities = list(pool.map(run, range(12)))
    assert len(set(identities)) == 1 and len(calls) == 1


def test_replacement_after_verification_retains_original_fd(cache_api, case):
    with case.invoke(cache_api) as lease:
        target = lease.path / "bin/worker"
        target.rename(lease.path / "bin/old")
        target.symlink_to(lease.path / "lib/data")
        assert os.read(lease.fds["bin/worker"], 100) == case.files["bin/worker"]
        assert lease.evidence["execution_race_closed"] is False
    with pytest.raises((ValueError, OSError)):
        case.invoke(cache_api, offline=True)


def test_unknown_backend_and_offline_miss_actionable(cache_api, case):
    case.document["backend"] = "unknown"
    with pytest.raises(cache_api.IncompleteError) as caught:
        case.invoke(cache_api)
    assert caught.value.evidence["status"] == "INCOMPLETE"
    assert "backend" in str(caught.value)
    case.document["backend"] = "managed-v1"
    with pytest.raises(cache_api.IncompleteError, match="offline"):
        case.invoke(cache_api, offline=True)


def test_stream_extra_and_short_bytes(cache_api, case):
    for archive in (case.archive + b"extra", case.archive[:-1]):
        with pytest.raises(ValueError):
            case.invoke(cache_api, reader=lambda archive=archive: io.BytesIO(archive))


def test_cache_root_symlink_rejected(cache_api, case):
    outside = case.root.parent / "outside"
    outside.mkdir()
    case.root.symlink_to(outside, target_is_directory=True)
    with pytest.raises((OSError, ValueError)):
        case.invoke(cache_api)
    assert not list(outside.iterdir())


@pytest.mark.parametrize("abi", ["3.11", "3.12", "3.13"])
def test_each_supported_abi_is_bound(cache_api, case, abi):
    case.document["abi"] = abi
    payload = canonical(case.document)
    pem = case.key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    signature = base64.b64encode(case.key.sign(payload)).decode()
    with cache_api.acquire(
        case.root,
        payload,
        signature,
        pem,
        abi=abi,
        backend="managed-v1",
        policy="deny-v1",
        reader=lambda: io.BytesIO(case.archive),
    ) as lease:
        assert lease.identity == digest(payload)
    with pytest.raises(ValueError, match="ABI"):
        cache_api.acquire(case.root, payload, signature, pem, abi="3.10", backend="managed-v1", policy="deny-v1")


def test_wrong_public_key_and_duplicate_json(cache_api, case):
    payload = canonical(case.document)
    pem = (
        ed25519.Ed25519PrivateKey.generate()
        .public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    )
    with pytest.raises(ValueError, match="signature"):
        cache_api.acquire(
            case.root,
            payload,
            base64.b64encode(case.key.sign(payload)).decode(),
            pem,
            abi="3.11",
            backend="managed-v1",
            policy="deny-v1",
        )
    duplicate = payload[:-1] + b',"os":"darwin"}'
    pem = case.key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with pytest.raises(ValueError, match="duplicate"):
        cache_api.acquire(
            case.root,
            duplicate,
            base64.b64encode(case.key.sign(duplicate)).decode(),
            pem,
            abi="3.11",
            backend="managed-v1",
            policy="deny-v1",
        )


def test_interrupted_publish_never_exposes_final(cache_api, case, monkeypatch):
    def interrupted(*_args, **_kwargs):
        raise KeyboardInterrupt

    with monkeypatch.context() as patch:
        patch.setattr(cache_api.os, "rename", interrupted)
        with pytest.raises(KeyboardInterrupt):
            case.invoke(cache_api)
    assert not [p for p in case.root.iterdir() if p.is_dir()]
    with pytest.raises(cache_api.IncompleteError, match="offline"):
        case.invoke(cache_api, offline=True)
    with case.invoke(cache_api):
        pass


def test_symlink_substitution_at_open_rejected(cache_api, case, monkeypatch):
    with case.invoke(cache_api) as lease:
        root = lease.path
    original = cache_api.os.open
    switched = []

    def switch(path, flags, *args, **kwargs):
        if path == "worker" and not switched:
            switched.append(True)
            (root / "bin/worker").unlink()
            (root / "bin/worker").symlink_to(root / "lib/data")
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(cache_api.os, "open", switch)
    with pytest.raises(OSError):
        case.invoke(cache_api, offline=True)
    assert switched


def test_link_added_during_digest_rejected(cache_api, case, monkeypatch):
    with case.invoke(cache_api) as lease:
        root = lease.path
    original = cache_api.os.read
    changed = []

    def read(fd, size):
        data = original(fd, size)
        if data == case.files["bin/worker"] and not changed:
            changed.append(True)
            os.link(root / "bin/worker", case.root.parent / "late-alias")
        return data

    monkeypatch.setattr(cache_api.os, "read", read)
    with pytest.raises(ValueError, match="changed"):
        case.invoke(cache_api, offline=True)
    assert changed


def test_archive_digest_and_reader_budget(cache_api, case):
    bad = bytearray(case.archive)
    bad[1024] ^= 1
    with pytest.raises(ValueError, match="archive digest"):
        case.invoke(cache_api, reader=lambda: io.BytesIO(bad))

    class Oversized(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            return b"x" * ((size or 0) + 1)

    with pytest.raises(ValueError, match="oversized"):
        case.invoke(cache_api, reader=lambda: Oversized())


def test_unused_link_descriptor_rejected(cache_api, case):
    raw = bytearray(case.archive)
    raw[157:167] = b"descriptor"
    raw[148:156] = b"        "
    raw[148:156] = f"{sum(raw[:512]):06o}\0 ".encode()
    case.archive = bytes(raw)
    case.document["archive"] = {"size": len(raw), "sha256": digest(raw)}
    with pytest.raises(ValueError, match="descriptor"):
        case.invoke(cache_api)


def test_process_death_leaves_unselectable_staging(cache_api, case):
    child = os.fork()
    if child == 0:
        extract = cache_api._extract

        def die_after_extraction(*args):
            extract(*args)
            os._exit(73)

        cache_api._extract = die_after_extraction
        case.invoke(cache_api)
        os._exit(74)
    _, status = os.waitpid(child, 0)
    assert os.waitstatus_to_exitcode(status) == 73
    assert len(list(case.root.glob("*.partial"))) == 1
    with pytest.raises(cache_api.IncompleteError, match="offline"):
        case.invoke(cache_api, offline=True)
    with case.invoke(cache_api) as lease:
        assert os.read(lease.fds["lib/data"], 100) == case.files["lib/data"]


def test_independent_processes_install_once(cache_api, case):
    count_file = case.root.parent / "reader-calls"
    children = []
    for _ in range(4):
        child = os.fork()
        if child == 0:

            def reader():
                fd = os.open(count_file, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
                os.write(fd, b"call\n")
                os.close(fd)
                return io.BytesIO(case.archive)

            try:
                with case.invoke(cache_api, reader=reader):
                    pass
            except BaseException:
                os._exit(1)
            os._exit(0)
        children.append(child)
    exits = [os.waitstatus_to_exitcode(os.waitpid(child, 0)[1]) for child in children]
    assert exits == [0] * 4
    assert count_file.read_bytes() == b"call\n"


def test_cleanup_failure_releases_root_descriptor(cache_api, case, monkeypatch):
    roots = []
    original = cache_api._root

    def track(path):
        fd = original(path)
        roots.append(fd)
        return fd

    def fail(*args):
        raise OSError("fixture I/O failure")

    monkeypatch.setattr(cache_api, "_root", track)
    monkeypatch.setattr(cache_api, "_extract", fail)
    monkeypatch.setattr(cache_api, "_remove", fail)
    with pytest.raises(OSError, match="fixture"):
        case.invoke(cache_api)
    with pytest.raises(OSError):
        os.fstat(roots[0])
