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


def test_provenance_binds_every_unchanged_member_and_license(prepared_wheel, packager):
    wheel, _, original = prepared_wheel
    receipt = json.loads(wheel.with_suffix(".provenance.json").read_bytes())
    unchanged = receipt["unchanged_members"]
    for name, data in original.items():
        if name.endswith(("/METADATA", "/WHEEL", "/RECORD")):
            continue
        assert unchanged[name] == {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
    license_path = "z3_solver-5.1.0.0.data/data/LICENSE.txt"
    assert receipt["licenses"][license_path] == unchanged[license_path]


def test_provenance_rejects_altered_source_with_valid_record(tmp_path, packager, monkeypatch):
    _path, original = source(tmp_path, packager, monkeypatch)
    files = packager.corrected_members(original)
    files["z3/z3.py"] = b"altered source"
    record_name = packager.DOWNSTREAM_DIST_INFO + "/RECORD"
    files[record_name] = record({k: v for k, v in files.items() if k != record_name}, record_name)
    data = packager.wheel_bytes(files)
    with pytest.raises(ValueError, match="payload"):
        packager.provenance(data, original)


def test_missing_license_is_an_explicit_admission_gap(tmp_path, packager, monkeypatch):
    _path, original = source(tmp_path, packager, monkeypatch)
    original = {k: v for k, v in original.items() if not k.endswith("LICENSE.txt")}
    record_name = packager.UPSTREAM_DIST_INFO + "/RECORD"
    original[record_name] = record({k: v for k, v in original.items() if k != record_name}, record_name)
    data = packager.wheel_bytes(packager.corrected_members(original))
    receipt = packager.provenance(data, original)
    assert receipt["license_payload_complete"] is False
    assert receipt["licenses"] == {}
    assert "missing_upstream_license_payload" in receipt["admission_gaps"]
    assert receipt["dependency_admitted"] is False


def test_reviewed_supplemental_license_is_bound_to_exact_tag_and_blob(packager):
    evidence = packager.reviewed_license_inputs()
    assert evidence["tag_commit"] == "0b6cdcdbc65da25ef0f73ac9da210574d0f66cf8"
    assert evidence["license_sha256"] == "e617cad2ab9347e3129c2b171e87909332174e17961c5c3412d0799469111337"
    assert evidence["license_git_blob"] == "cc90bed7477d0809f4309b718e920d411e1f3da8"
    assert evidence["source_commit_signature_verified"] is True


def test_supplemental_license_tamper_rejects(tmp_path, packager, monkeypatch):
    license_file = tmp_path / "LICENSE.txt"
    license_file.write_bytes(b"guessed license text")
    monkeypatch.setattr(packager, "LICENSE_INPUT", license_file)
    with pytest.raises(ValueError, match=r"license.*digest"):
        packager.reviewed_license_inputs()


def test_release_archive_hash_rejects_before_parsing(tmp_path, packager):
    archive = tmp_path / "release.zip"
    archive.write_bytes(b"not a zip")
    with pytest.raises(ValueError, match=r"release.*digest"):
        packager.release_license_evidence({}, archive)


def test_release_member_mismatch_rejects_even_with_valid_archive_hash(tmp_path, packager, monkeypatch):
    archive = tmp_path / "release.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("z3-5.1.0-arm64-osx-13.3/LICENSE.txt", packager.LICENSE_INPUT.read_bytes())
        output.writestr("z3-5.1.0-arm64-osx-13.3/bin/python/z3/z3.py", b"wrong source")
    monkeypatch.setattr(packager, "RELEASE_SHA256", hashlib.sha256(archive.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="linkage"):
        packager.release_license_evidence({"z3/z3.py": b"different source"}, archive)


def test_license_replacement_before_output_is_not_relabelled_as_verified(tmp_path, packager, monkeypatch):
    path, _original = source(tmp_path, packager, monkeypatch)
    replaced = tmp_path / "replaced-license.txt"
    replaced.write_bytes(b"unauthenticated replacement")
    monkeypatch.setattr(packager, "LICENSE_INPUT", replaced)
    monkeypatch.setattr(packager, "provenance", lambda *_args: {"z3_source_and_native_license_verified": True})
    with pytest.raises(ValueError, match="license digest"):
        packager.prepare(path, tmp_path / "out", release_archive=tmp_path / "unused.zip")
    assert not (tmp_path / "out").exists()


@pytest.fixture(name="projection_inputs")
def fixture_projection_inputs(tmp_path, packager, monkeypatch):
    evidence: dict = packager.reviewed_license_inputs()
    foreign = {name: ("inert foreign payload:" + name).encode() for name in evidence["unlinked_non_darwin_payload"]}

    def project_source(files):
        del files["z3_solver-5.1.0.0.data/data/LICENSE.txt"]
        files.update(foreign)

    path, original = source(tmp_path, packager, monkeypatch, change=project_source)
    evidence = dict(
        evidence,
        tagged_source_sha256=hashlib.sha256(original["z3/z3.py"]).hexdigest(),
        unlinked_non_darwin_payload={
            name: {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)} for name, data in foreign.items()
        },
    )
    monkeypatch.setattr(packager, "reviewed_license_inputs", lambda: evidence)
    release = tmp_path / "authenticated-fixture-release.zip"
    with zipfile.ZipFile(release, "w") as archive:
        archive.writestr(evidence["license_release_member"], packager.LICENSE_INPUT.read_bytes())
        for name, data in original.items():
            if member := packager._release_member(name):
                archive.writestr(member, data)
    monkeypatch.setattr(packager, "RELEASE_SHA256", hashlib.sha256(release.read_bytes()).hexdigest())
    return path, release, original


def test_darwin_projection_omits_exact_foreign_payload_and_retains_native_source(tmp_path, packager, projection_inputs):
    path, release, original = projection_inputs
    wheel = packager.prepare(path, tmp_path / "projected", release_archive=release, darwin_only=True)
    assert wheel.name == "z3_solver-5.1.0.0+specfact.2-py3-none-macosx_14_0_arm64.whl"
    files = packager.read_members(wheel.read_bytes())
    assert not any(name.endswith(".dll") for name in files)
    for name, content in original.items():
        if not name.endswith(".dll") and not name.startswith(packager.UPSTREAM_DIST_INFO + "/"):
            assert files[name] == content
    prefix = "z3_solver-5.1.0.0+specfact.2.dist-info"
    assert files[prefix + "/licenses/LICENSE.txt"] == packager.LICENSE_INPUT.read_bytes()
    assert b"Version: 5.1.0.0+specfact.2\n" in files[prefix + "/METADATA"]
    assert b"License-File: licenses/LICENSE.txt\n" in files[prefix + "/METADATA"]
    packager.verify_record(files, prefix)


@pytest.fixture(name="projection_receipt")
def fixture_projection_receipt(tmp_path, packager, projection_inputs):
    path, release, original = projection_inputs
    wheel = packager.prepare(path, tmp_path / "projected", release_archive=release, darwin_only=True)
    return wheel, json.loads(wheel.with_suffix(".provenance.json").read_bytes()), original


def test_projection_provenance_retains_verification_without_admission(projection_receipt):
    _, receipt, _ = projection_receipt
    assert receipt["schema_version"] == 4
    assert receipt["license_payload_complete"] is True
    assert receipt["z3_source_and_native_license_verified"] is True
    assert len(receipt["omitted_members"]) == 10
    assert not any(name.endswith(".dll") for name in receipt["unchanged_members"])
    assert receipt["admission_gaps"] == []
    assert receipt["dependency_admitted"] is False and receipt["production_eligible"] is False


def test_projection_provenance_binds_omissions_and_license(packager, projection_receipt):
    wheel, receipt, original = projection_receipt
    assert receipt["output"]["sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert receipt["upstream"]["sha256"] == packager.UPSTREAM_SHA256
    for name, identity in receipt["omitted_members"].items():
        assert identity == {"sha256": hashlib.sha256(original[name]).hexdigest(), "size": len(original[name])}
    license_identity = receipt["licenses"]["z3_solver-5.1.0.0+specfact.2.dist-info/licenses/LICENSE.txt"]
    assert license_identity["sha256"] == packager.LICENSE_SHA256


def test_projection_is_deterministic_and_historical_derivative_remains_available(tmp_path, packager, projection_inputs):
    path, release, original = projection_inputs
    first = packager.prepare(path, tmp_path / "one", release_archive=release, darwin_only=True)
    second = packager.prepare(path, tmp_path / "two", release_archive=release, darwin_only=True)
    assert first.read_bytes() == second.read_bytes()
    assert first.with_suffix(".provenance.json").read_bytes() == second.with_suffix(".provenance.json").read_bytes()
    legacy = packager.prepare(path, tmp_path / "legacy")
    assert legacy.name == packager.OUTPUT_FILENAME
    legacy_files = packager.read_members(legacy.read_bytes())
    assert all(legacy_files[name] == data for name, data in original.items() if name.endswith(".dll"))


def test_projection_without_authenticated_release_rejects_before_output(tmp_path, packager, projection_inputs):
    path, _, _ = projection_inputs
    with pytest.raises(ValueError, match="release archive required"):
        packager.prepare(path, tmp_path / "projected", darwin_only=True)
    assert not (tmp_path / "projected").exists()


@pytest.mark.parametrize(
    "mutation",
    [("foreign", b"changed"), ("foreign", None), ("z3/lib/unknown.dll", b"unreviewed"), ("z3/z3.py", b"changed")],
    ids=["changed_dll", "missing_dll", "extra_dll", "changed_source"],
)
def test_projection_rejects_unreviewed_payload_before_output(
    tmp_path, packager, projection_inputs, monkeypatch, mutation
):
    path, release, original = projection_inputs
    member, replacement = mutation
    name = next(name for name in original if name.endswith(".dll")) if member == "foreign" else member
    files = dict(original)
    if replacement is None:
        del files[name]
    else:
        files[name] = replacement
    record_name = packager.UPSTREAM_DIST_INFO + "/RECORD"
    files[record_name] = record({k: v for k, v in files.items() if k != record_name}, record_name)
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    monkeypatch.setattr(packager, "UPSTREAM_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError):
        packager.prepare(path, tmp_path / "projected", release_archive=release, darwin_only=True)
    assert not (tmp_path / "projected").exists()


def test_projection_rejects_changed_license_before_output(tmp_path, packager, projection_inputs, monkeypatch):
    path, release, _ = projection_inputs
    license_input = tmp_path / "tampered-license.txt"
    license_input.write_bytes(b"unverified text")
    monkeypatch.setattr(packager, "LICENSE_INPUT", license_input)
    with pytest.raises(ValueError):
        packager.prepare(path, tmp_path / "projected", release_archive=release, darwin_only=True)
    assert not (tmp_path / "projected").exists()
