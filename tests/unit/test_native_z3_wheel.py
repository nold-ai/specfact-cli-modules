"""Contract tests for authenticated, deterministic downstream Z3 preparation."""

import base64
import csv
import hashlib
import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest


@pytest.fixture(name="packager")
def fixture_packager():
    path = Path(__file__).parents[2] / "scripts/native_z3_wheel.py"
    spec = importlib.util.spec_from_file_location("native_z3_wheel", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(files, record_name):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name, data in sorted(files.items()):
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=" + digest, str(len(data))])
    writer.writerow([record_name, "", ""])
    return stream.getvalue().encode()


def source(tmp_path, packager, monkeypatch, change=None, extra=None):
    prefix = packager.UPSTREAM_DIST_INFO
    files = {
        prefix + "/METADATA": packager.EXPECTED_METADATA,
        prefix + "/WHEEL": packager.EXPECTED_WHEEL,
        prefix + "/top_level.txt": b"z3\n",
        "z3/lib/libz3.dylib": b"native bytes\x00\xff",
        "z3/z3.py": b"raise RuntimeError('never execute input')\n",
        "z3_solver-5.1.0.0.data/data/LICENSE.txt": b"MIT license bytes",
    }
    if change:
        change(files)
    files[prefix + "/RECORD"] = record(files, prefix + "/RECORD")
    path = tmp_path / "input.whl"
    with zipfile.ZipFile(path, "w") as output:
        for name, data in files.items():
            output.writestr(name, data)
        if extra:
            _write_extra_member(output, files, extra)
    monkeypatch.setattr(packager, "UPSTREAM_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    return path, files


def _write_extra_member(output, files, extra):
    if isinstance(extra[0], str) and extra[0] in files:
        with pytest.warns(UserWarning, match="Duplicate name"):
            output.writestr(*extra)
        return
    output.writestr(*extra)


@pytest.fixture(name="prepared_wheel")
def fixture_prepared_wheel(tmp_path, packager, monkeypatch):
    path, original = source(tmp_path, packager, monkeypatch)
    wheel = packager.prepare(path, tmp_path / "out")
    with zipfile.ZipFile(wheel) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    return wheel, files, original


def test_deterministic_wheel_and_provenance(tmp_path, packager, monkeypatch):
    path, _ = source(tmp_path, packager, monkeypatch)
    wheels = [packager.prepare(path, tmp_path / name) for name in ("one", "two")]
    assert wheels[0].read_bytes() == wheels[1].read_bytes()
    receipts = [wheel.with_suffix(".provenance.json").read_bytes() for wheel in wheels]
    assert receipts[0] == receipts[1]


def test_exact_output_digest_and_filename(prepared_wheel):
    wheel, _, _ = prepared_wheel
    assert wheel.name == "z3_solver-5.1.0.0+specfact.1-py3-none-macosx_14_0_arm64.whl"
    # Captured from the pre-refactor implementation using this synthetic payload.
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == (
        "273a2740569f381097a972ba6cddd03315d692b2669d4964c6527d273b59e5c9"
    )


def test_all_unmodified_payload_bytes(prepared_wheel, packager):
    _, files, original = prepared_wheel
    expected = {
        name.replace(packager.UPSTREAM_DIST_INFO, packager.DOWNSTREAM_DIST_INFO): data
        for name, data in original.items()
        if not name.endswith(("/METADATA", "/WHEEL", "/RECORD"))
    }
    actual = {name: data for name, data in files.items() if not name.endswith(("/METADATA", "/WHEEL", "/RECORD"))}
    assert actual == expected


def test_corrected_wheel_headers(prepared_wheel, packager):
    _, files, _ = prepared_wheel
    prefix = packager.DOWNSTREAM_DIST_INFO
    assert b"Version: 5.1.0.0+specfact.1\n" in files[prefix + "/METADATA"]
    assert b"Tag: py3-none-macosx_14_0_arm64\n" in files[prefix + "/WHEEL"]
    assert b"Root-Is-Purelib: false\n" in files[prefix + "/WHEEL"]


def test_record_membership_and_unhashed_self_row(prepared_wheel, packager):
    _, files, _ = prepared_wheel
    record_name = packager.DOWNSTREAM_DIST_INFO + "/RECORD"
    rows = list(csv.reader(io.StringIO(files[record_name].decode())))
    assert len(rows) == len(files)
    assert {row[0] for row in rows} == set(files)
    assert [row for row in rows if row[0] == record_name] == [[record_name, "", ""]]


def test_record_payload_digests_and_sizes(prepared_wheel, packager):
    _, files, _ = prepared_wheel
    record_name = packager.DOWNSTREAM_DIST_INFO + "/RECORD"
    rows = csv.reader(io.StringIO(files[record_name].decode()))
    for name, digest, size in rows:
        if name == record_name:
            continue
        expected = base64.urlsafe_b64encode(hashlib.sha256(files[name]).digest()).rstrip(b"=").decode()
        assert digest == "sha256=" + expected
        assert size == str(len(files[name]))


def test_provenance_binds_digests_without_admission(prepared_wheel, packager):
    wheel, _, _ = prepared_wheel
    receipt = json.loads(wheel.with_suffix(".provenance.json").read_bytes())
    assert receipt["production_eligible"] is False
    assert receipt["dependency_admitted"] is False
    assert receipt["upstream"]["sha256"] == packager.UPSTREAM_SHA256
    assert receipt["output"]["sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert receipt["corrections"]


def test_cli_prints_output_path(tmp_path, packager, monkeypatch, capsys):
    path, _ = source(tmp_path, packager, monkeypatch)
    destination = tmp_path / "out"
    monkeypatch.setattr("sys.argv", ["native_z3_wheel.py", str(path), str(destination)])
    packager.main()
    captured = capsys.readouterr()
    assert captured.out == str(destination / packager.OUTPUT_FILENAME) + "\n"
    assert captured.err == ""


def test_digest_tamper(tmp_path, packager, monkeypatch):
    path, _ = source(tmp_path, packager, monkeypatch)
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="digest"):
        packager.prepare(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "name", ["../escape", "/absolute", "z3/../escape", "z3\\escape", "z3//escape", "z3/lib/libz3.dylib"]
)
def test_unsafe_paths_duplicates(tmp_path, packager, monkeypatch, name):
    path, _ = source(tmp_path, packager, monkeypatch, extra=(name, b"bad"))
    with pytest.raises(ValueError):
        packager.prepare(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("member", ["METADATA", "WHEEL"])
def test_unexpected_wheel_headers(tmp_path, packager, monkeypatch, member):
    def change(files):
        files[packager.UPSTREAM_DIST_INFO + "/" + member] += b"Unexpected: value\n"

    path, _ = source(tmp_path, packager, monkeypatch, change)
    with pytest.raises(ValueError, match="metadata"):
        packager.prepare(path, tmp_path / "out")


def test_symlink_and_expansion(tmp_path, packager, monkeypatch):
    link = zipfile.ZipInfo("z3/link")
    link.create_system = 3
    link.external_attr = 0o120777 << 16
    path, _ = source(tmp_path, packager, monkeypatch, extra=(link, b"target"))
    with pytest.raises(ValueError):
        packager.prepare(path, tmp_path / "links")
    path, _ = source(tmp_path, packager, monkeypatch)
    monkeypatch.setattr(packager, "MAX_EXPANDED_BYTES", 10)
    with pytest.raises(ValueError, match="limit"):
        packager.prepare(path, tmp_path / "large")


def test_invalid_record_and_payload_tamper(tmp_path, packager, monkeypatch):
    path, files = source(tmp_path, packager, monkeypatch)
    files["z3/lib/libz3.dylib"] = b"altered"
    with zipfile.ZipFile(path, "w") as output:
        for name, data in files.items():
            output.writestr(name, data)
    monkeypatch.setattr(packager, "UPSTREAM_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="RECORD"):
        packager.prepare(path, tmp_path / "out")


def test_no_overwrite(tmp_path, packager, monkeypatch):
    path, _ = source(tmp_path, packager, monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    sentinel = out / "user.txt"
    sentinel.write_text("keep")
    with pytest.raises(FileExistsError):
        packager.prepare(path, out)
    assert sentinel.read_text() == "keep"
