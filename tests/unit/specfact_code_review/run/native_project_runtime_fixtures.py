"""Shared byte-exact native project fixture builders."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import struct
import sys
import tarfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from specfact_code_review.run.runtime_models import ProjectPlan


__all__ = [
    "_ACQUISITION_SOURCE",
    "_CPU_ARM64",
    "_CPU_X86_64",
    "_LC_LOAD_DYLIB",
    "_LC_RPATH",
    "_DownloadResponse",
    "_authenticated_bundle",
    "_bundle",
    "_download_archive_bytes",
    "_fat_macho",
    "_macho_string_command",
    "_thin_macho",
]

_CPU_ARM64 = 0x0100000C

_CPU_X86_64 = 0x01000007

_LC_LOAD_DYLIB = 0xC

_LC_RPATH = 0x8000001C

_ACQUISITION_SOURCE = Path(__file__).resolve().parents[4] / "scripts/macos_managed_boundary/project_acquisition.py"


def _macho_string_command(command: int, value: str, *, value_offset: int) -> bytes:
    encoded = value.encode("utf-8") + b"\0"
    size = (value_offset + len(encoded) + 7) & ~7
    payload = bytearray(size)
    struct.pack_into("<III", payload, 0, command, size, value_offset)
    payload[value_offset : value_offset + len(encoded)] = encoded
    return bytes(payload)


def _thin_macho(
    *,
    cpu: int = _CPU_ARM64,
    filetype: int = 8,
    loads: tuple[str, ...] = (),
    rpaths: tuple[str, ...] = (),
) -> bytes:
    commands = [_macho_string_command(_LC_LOAD_DYLIB, name, value_offset=24) for name in loads]
    commands.extend(_macho_string_command(_LC_RPATH, path, value_offset=12) for path in rpaths)
    body = b"".join(commands)
    return struct.pack("<8I", 0xFEEDFACF, cpu, 0, filetype, len(commands), len(body), 0, 0) + body


def _fat_macho(*slices: tuple[int, bytes]) -> bytes:
    table_size = 8 + len(slices) * 20
    offset = (table_size + 7) & ~7
    table = bytearray(struct.pack(">II", 0xCAFEBABE, len(slices)))
    payload = bytearray(offset)
    payload[:8] = table
    entries = bytearray()
    for cpu, image in slices:
        entries.extend(struct.pack(">IIIII", cpu, 0, offset, len(image), 3))
        payload.extend(image)
        offset += len(image)
        padding = (-offset) % 8
        payload.extend(b"\0" * padding)
        offset += padding
    payload[8 : 8 + len(entries)] = entries
    return bytes(payload)


def _bundle(root: Path, plan: ProjectPlan) -> Path:
    bundle = root / "bundle"
    (bundle / "locks").mkdir(parents=True)
    (bundle / "wheelhouse").mkdir()
    descriptor = {
        "schema": "specfact-macos-project-acquisition-v1",
        "corpus_identity": plan.identity,
        "abi": "cp312",
        "platform": "macos-arm64",
        "manager": {"name": "pip", "version": "26.2.1"},
        "content_sha256": "a" * 64,
        "signature": {"algorithm": "Ed25519-SHA256", "key_id": "b" * 64, "value": "fixture"},
    }
    (bundle / "descriptor.json").write_text(json.dumps(descriptor), encoding="utf-8")
    (bundle / "locks/pip.json").write_text("{}", encoding="utf-8")
    return bundle


def _authenticated_bundle(root: Path, plan: ProjectPlan, capsule: Path) -> Path:
    spec = importlib.util.spec_from_file_location("focused_project_acquisition", _ACQUISITION_SOURCE)
    assert spec is not None and spec.loader is not None
    acquisition = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = acquisition
    spec.loader.exec_module(acquisition)
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    trust = capsule / "trust"
    trust.mkdir(parents=True)
    public_key = trust / "project-acquisition-public.pem"
    public_key.write_bytes(public_pem)
    public_key.chmod(0o444)
    source_archive = root / "source-input.tar.gz"
    root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source_archive, "w:gz") as archive:
        payload = b"[project]\nname='fixture'\nversion='1.0'\n"
        member = tarfile.TarInfo("project/pyproject.toml")
        member.size = len(payload)
        member.mode = 0o644
        member.mtime = 0
        archive.addfile(member, io.BytesIO(payload))
    wheel = root / "fixture_dep-2.0-py3-none-any.whl"
    wheel.write_bytes(b"authenticated wheel fixture")
    commit = "1" * 40
    request = {
        "schema": "specfact-macos-project-acquisition-request-v1",
        "project": "fixture",
        "corpus_identity": plan.identity,
        "source": {
            "url": "https://github.com/example/fixture.git",
            "commit": commit,
            "archive_url": f"https://github.com/example/fixture/archive/{commit}.tar.gz",
        },
        "manager": {"name": "pip", "version": "26.2.1"},
        "selection": {"groups": ["default"], "environment": "default"},
        "abi": "cp312",
        "platform": "macos-arm64",
        "network": "trusted-acquisition-only",
        "execute_project_code": False,
    }

    def sign(payload: bytes) -> dict[str, str]:
        return {
            "algorithm": "Ed25519-SHA256",
            "key_id": hashlib.sha256(public_pem).hexdigest(),
            "value": base64.b64encode(private_key.sign(payload)).decode("ascii"),
        }

    def verify_source(selected: dict[str, Any], archive_sha256: str, tree_sha256: str) -> dict[str, Any]:
        return {
            "schema": "specfact-trusted-source-fetch-v1",
            "method": "github-commit-api-and-archive",
            "source_url": selected["source"]["url"],
            "archive_url": selected["source"]["archive_url"],
            "commit": selected["source"]["commit"],
            "git_tree": "2" * 40,
            "archive_sha256": archive_sha256,
            "tree_sha256": tree_sha256,
            "authenticated_transport": True,
        }

    destination = root / "signed-bundle"
    acquisition.create_acquisition_bundle(
        request,
        source_archive,
        artifacts=[
            {
                "package": "fixture-dep",
                "version": "2.0",
                "filename": wheel.name,
                "url": f"https://files.pythonhosted.org/packages/aa/{wheel.name}",
                "path": wheel,
                "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            }
        ],
        destination=destination,
        signer=sign,
        source_verifier=verify_source,
    )
    return destination


def _download_archive_bytes() -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        payload = b"fixture"
        member = tarfile.TarInfo("bundle/fixture.txt")
        member.size = len(payload)
        member.mode = 0o600
        archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


class _DownloadResponse(io.BytesIO):
    def __init__(self, payload: bytes) -> None:
        super().__init__(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
