#!/usr/bin/env python3
"""Prepare one pinned, experimental downstream Z3 wheel without executing input.

Usage: python scripts/native_z3_wheel.py INPUT.whl NEW_OUTPUT_DIRECTORY
The output directory must not exist. Native inventory and dependency resolution
remain separate gates; this tool grants no production or dependency admission.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import shutil
import stat
import sys
import zipfile
from pathlib import Path


UPSTREAM_URL = (
    "https://files.pythonhosted.org/packages/01/9a/"
    "cdb6db09d6aff6a803a94505aa24666db5e47df7aad0f2b1b0ddcb52ed12/"
    "z3_solver-5.1.0.0-py3-none-macosx_13_0_arm64.whl"
)
UPSTREAM_SHA256 = "399a38a85d784105e5df5a05c04a581481bfdb80af7424779cf76fa843b4e66c"
UPSTREAM_DIST_INFO = "z3_solver-5.1.0.0.dist-info"
DOWNSTREAM_DIST_INFO = "z3_solver-5.1.0.0+specfact.1.dist-info"
OUTPUT_FILENAME = "z3_solver-5.1.0.0+specfact.1-py3-none-macosx_14_0_arm64.whl"
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_EXPANDED_BYTES = 160 * 1024 * 1024
MAX_MEMBERS = 256
# Exact metadata observed after authenticating the official PyPI artifact.
EXPECTED_METADATA = (
    b"Metadata-Version: 2.4\n"
    b"Name: z3-solver\n"
    b"Version: 5.1.0.0\n"
    b"Summary: an efficient SMT solver library\n"
    b"Home-page: https://github.com/Z3Prover/z3\n"
    b"Author: The Z3 Theorem Prover Project\n"
    b"Maintainer: Audrey Dutcher and Nikolaj Bjorner\n"
    b"Maintainer-email: audrey@rhelmot.io\n"
    b"License: MIT License\n"
    b"Keywords: z3,smt,sat,prover,theorem\n"
    b'Requires-Dist: importlib-resources; python_version < "3.9"\n'
    b"Dynamic: author\n"
    b"Dynamic: description\n"
    b"Dynamic: home-page\n"
    b"Dynamic: keywords\n"
    b"Dynamic: license\n"
    b"Dynamic: maintainer\n"
    b"Dynamic: maintainer-email\n"
    b"Dynamic: requires-dist\n"
    b"Dynamic: summary\n"
    b"\n"
    b"Z3 is a theorem prover from Microsoft Research with support for bitvectors, booleans, arrays, "
    b"floating point numbers, strings, and other data types.\n"
    b"\n"
    b"For documentation, please read http://z3prover.github.io/api/html/z3.html\n"
)
EXPECTED_WHEEL = (
    b"Wheel-Version: 1.0\nGenerator: setuptools (84.0.0)\nRoot-Is-Purelib: true\nTag: py3-none-macosx_13_3_arm64\n\n"
)


def digest(data: bytes) -> str:
    """Return the wheel RECORD SHA-256 representation."""
    return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


def read_authenticated(source: Path) -> bytes:
    """Bound input allocation and authenticate before ZIP parsing."""
    with source.open("rb") as stream:
        data = stream.read(MAX_ARCHIVE_BYTES + 1)
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("archive size limit exceeded")
    if hashlib.sha256(data).hexdigest() != UPSTREAM_SHA256:
        raise ValueError("upstream digest mismatch")
    return data


def _canonical_member_name(member: zipfile.ZipInfo) -> bool:
    """Accept only unchanged, printable relative paths with canonical components."""
    name = member.filename
    return not (
        name != member.orig_filename
        or "\\" in name
        or ":" in name
        or any(part in ("", ".", "..") for part in name.split("/"))
        or any(ord(char) < 32 or ord(char) > 126 for char in name)
    )


def _validate_member(member: zipfile.ZipInfo, seen_names: set[str]) -> None:
    """Reject aliases, nonregular entries, encryption and unsupported compression."""
    name = member.filename
    if not _canonical_member_name(member) or name.casefold() in seen_names:
        raise ValueError(f"unsafe ZIP member: {name!r}")
    mode = member.external_attr >> 16
    if (
        stat.S_IFMT(mode) not in (0, stat.S_IFREG)
        or member.flag_bits & 1
        or member.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
    ):
        raise ValueError(f"unsafe ZIP member: {name!r}")


def _read_member_payload(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> bytes:
    """Bound each decompressed read and require the declared payload length."""
    with archive.open(member) as stream:
        payload = stream.read(member.file_size + 1)
    if len(payload) != member.file_size:
        raise ValueError("ZIP member size mismatch")
    return payload


def read_members(data: bytes) -> dict[str, bytes]:
    """Reject noncanonical paths, links, duplicate members and expansion bombs."""
    files: dict[str, bytes] = {}
    seen_names: set[str] = set()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) > MAX_MEMBERS or sum(m.file_size for m in members) > MAX_EXPANDED_BYTES:
            raise ValueError("ZIP expansion or member limit exceeded")
        for member in members:
            _validate_member(member, seen_names)
            files[member.filename] = _read_member_payload(archive, member)
            seen_names.add(member.filename.casefold())
    return files


def verify_record(files: dict[str, bytes], prefix: str) -> None:
    """Require one correct SHA-256/size row per file and an unhashed RECORD row."""
    name = prefix + "/RECORD"
    try:
        rows = list(csv.reader(io.StringIO(files[name].decode("utf-8")), strict=True))
    except (KeyError, UnicodeError, csv.Error) as exc:
        raise ValueError("missing or malformed RECORD") from exc
    seen: set[str] = set()
    for row in rows:
        if len(row) != 3 or row[0] in seen or row[0] not in files:
            raise ValueError("invalid RECORD membership")
        path, hashed, size = row
        expected = ("", "") if path == name else (digest(files[path]), str(len(files[path])))
        if (hashed, size) != expected:
            raise ValueError(f"invalid RECORD digest or size: {path}")
        seen.add(path)
    if seen != set(files):
        raise ValueError("incomplete RECORD")


def corrected_members(files: dict[str, bytes]) -> dict[str, bytes]:
    """Change only approved metadata, dist-info names and regenerated RECORD."""
    prefix = UPSTREAM_DIST_INFO
    if files.get(prefix + "/METADATA") != EXPECTED_METADATA or files.get(prefix + "/WHEEL") != EXPECTED_WHEEL:
        raise ValueError("unexpected upstream metadata")
    if any(".dist-info" in name and not name.startswith(prefix + "/") for name in files):
        raise ValueError("unexpected dist-info metadata directory")
    if any(name.endswith(("/RECORD.jws", "/RECORD.p7s")) for name in files):
        raise ValueError("unexpected signed metadata")
    verify_record(files, prefix)
    result = {
        (DOWNSTREAM_DIST_INFO + name[len(prefix) :] if name.startswith(prefix + "/") else name): data
        for name, data in files.items()
        if name != prefix + "/RECORD"
    }
    result[DOWNSTREAM_DIST_INFO + "/METADATA"] = EXPECTED_METADATA.replace(
        b"Version: 5.1.0.0\n", b"Version: 5.1.0.0+specfact.1\n"
    )
    result[DOWNSTREAM_DIST_INFO + "/WHEEL"] = EXPECTED_WHEEL.replace(
        b"Root-Is-Purelib: true\n", b"Root-Is-Purelib: false\n"
    ).replace(b"Tag: py3-none-macosx_13_3_arm64\n", b"Tag: py3-none-macosx_14_0_arm64\n")
    record_name = DOWNSTREAM_DIST_INFO + "/RECORD"
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name, data in sorted(result.items()):
        writer.writerow([name, digest(data), str(len(data))])
    writer.writerow([record_name, "", ""])
    result[record_name] = stream.getvalue().encode("utf-8")
    verify_record(result, DOWNSTREAM_DIST_INFO)
    return result


def wheel_bytes(files: dict[str, bytes]) -> bytes:
    """Use sorted, stored members and fixed ZIP attributes for reproducible bytes."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.create_system = 3
            member.external_attr = 0o100644 << 16
            archive.writestr(member, data)
    data = stream.getvalue()
    # Independently read the serialized archive, not just the pre-ZIP mapping.
    restored = read_members(data)
    if restored != files:
        raise ValueError("output payload mismatch")
    verify_record(restored, DOWNSTREAM_DIST_INFO)
    return data


def provenance(data: bytes) -> dict:
    """Bind the observed upstream metadata and exact documented corrections."""
    return {
        "schema_version": 1,
        "production_eligible": False,
        "dependency_admitted": False,
        "upstream": {"url": UPSTREAM_URL, "sha256": UPSTREAM_SHA256},
        "output": {"filename": OUTPUT_FILENAME, "sha256": hashlib.sha256(data).hexdigest()},
        "corrections": {
            "METADATA.Version": {"from": "5.1.0.0", "to": "5.1.0.0+specfact.1"},
            "WHEEL.Tag": {"from": "py3-none-macosx_13_3_arm64", "to": "py3-none-macosx_14_0_arm64"},
            "WHEEL.Root-Is-Purelib": {"from": True, "to": False},
            "dist-info": {"from": UPSTREAM_DIST_INFO, "to": DOWNSTREAM_DIST_INFO},
            "filename_platform": {"from": "macosx_13_0_arm64", "to": "macosx_14_0_arm64"},
            "RECORD": "regenerated SHA-256 and sizes for every member; RECORD row unhashed",
        },
        "payload": "all other member bytes unchanged, including native code, source and licenses",
        "limitations": "native minimum OS/architecture inventory and resolver/pip check remain separate gates",
    }


def prepare(source: Path, destination: Path) -> Path:
    """Authenticate and validate fully before creating an exclusive output directory."""
    files = corrected_members(read_members(read_authenticated(source)))
    data = wheel_bytes(files)
    receipt = json.dumps(provenance(data), indent=2, sort_keys=True) + "\n"
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    output = destination / OUTPUT_FILENAME
    try:
        with output.open("xb") as stream:
            stream.write(data)
        with output.with_suffix(".provenance.json").open("x", encoding="utf-8") as stream:
            stream.write(receipt)
    except BaseException:
        shutil.rmtree(destination)
        raise
    return output


def main() -> None:
    """Run the offline preparation CLI; input is never imported or executed."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        output = prepare(args.source, args.destination)
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"Z3 preparation failed: {exc}\n")
    sys.stdout.write(os.fspath(output) + "\n")


if __name__ == "__main__":
    main()
