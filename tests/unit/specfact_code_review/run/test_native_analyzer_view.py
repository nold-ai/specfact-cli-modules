"""File-based analyzers get the same bounded dependency domain as Python imports."""

import os
from importlib.metadata import Distribution, PackagePath
from pathlib import Path
from typing import Any

import pytest

from specfact_code_review.run import native_analyzer_view


def _recorded_site(tmp_path: Path, records: list[str]) -> tuple[Path, Path, dict[str, Any]]:
    site = tmp_path / "capsule/site-packages"
    (site / "owned").mkdir(parents=True)
    (site / "owned/__init__.py").write_text("VALUE = 1\n")
    info = site / "owned-1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: owned\nVersion: 1\n")
    (info / "RECORD").write_text(
        "owned/__init__.py,,\nowned-1.dist-info/METADATA,,\nowned-1.dist-info/RECORD,,\n"
        + "".join(f"{name},,\n" for name in records)
    )
    graph = {"sealed_imports": ["owned"], "installed": [{"name": "owned", "version": "1", "origin": "analyzer"}]}
    return site, tmp_path / "view", graph


def test_project_origin_pytest_can_have_no_analyzer_fallback(tmp_path: Path):
    site = tmp_path / "capsule-site"
    site.mkdir()
    (site / "unrelated_analyzer.py").write_text("VALUE = 2\n")
    graph = {"sealed_imports": [], "installed": [{"name": "pytest", "version": "9.0.3", "origin": "project"}]}
    target = tmp_path / "view"
    native_analyzer_view.build_analyzer_view(site, target, graph)
    assert not list(target.iterdir())
    assert not target.stat().st_mode & 0o222


def test_view_contains_only_admitted_imports_and_metadata(tmp_path: Path) -> None:
    site = tmp_path / "capsule/site-packages"
    (site / "owned").mkdir(parents=True)
    (site / "owned/__init__.py").write_text("VALUE = 1\n")
    (site / "unrelated.py").write_text("VALUE = 2\n")
    info = site / "owned-1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: owned\nVersion: 1\n")
    (info / "RECORD").write_text("owned/__init__.py,,\nowned-1.dist-info/METADATA,,\n")
    graph = {"sealed_imports": ["owned"], "installed": [{"name": "owned", "version": "1", "origin": "analyzer"}]}
    target = tmp_path / "view"
    native_analyzer_view.build_analyzer_view(site, target, graph)
    assert (target / "owned/__init__.py").is_file()
    assert (target / "owned-1.dist-info/METADATA").is_file()
    assert not (target / "unrelated.py").exists()
    assert not target.stat().st_mode & 0o222


def test_view_rejects_symlinked_analyzer_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (tmp_path / "host.py").write_text("VALUE = 1\n")
    (source / "owned.py").symlink_to(tmp_path / "host.py")
    info = source / "owned-1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: owned\nVersion: 1\n")
    (info / "RECORD").write_text("owned.py,,\nowned-1.dist-info/METADATA,,\n")
    with pytest.raises(ValueError, match="indirection"):
        native_analyzer_view.build_analyzer_view(
            source,
            tmp_path / "view",
            {
                "sealed_imports": ["owned"],
                "installed": [{"name": "owned", "version": "1", "origin": "analyzer"}],
            },
        )


@pytest.mark.parametrize(
    "omitted",
    [
        "owned/__pycache__/__init__.cpython-313.pyc",
        "owned/__pycache__/__init__.cpython-313.opt-1.pyc",
        "owned/.pyc",
        "owned/legacy.pyo",
        "owned/windows.dll",
        "owned/windows.exe",
        "semgrep/bin/semgrep-pro",
        "semgrep/bin/experimental/helper",
        "z3/lib/libz3.5.1.dylib",
    ],
)
def test_retained_record_allows_only_explicit_preparation_omissions(tmp_path: Path, omitted: str) -> None:
    site, target, graph = _recorded_site(tmp_path, [omitted, "z3/lib/libz3.dylib"])
    library = site / "z3/lib/libz3.dylib"
    library.parent.mkdir(parents=True)
    library.write_bytes(b"admitted canonical library")
    (site / "injected.py").write_text("raise RuntimeError('unrecorded injection')\n")

    native_analyzer_view.build_analyzer_view(site, target, graph)

    assert (target / "owned/__init__.py").read_text() == "VALUE = 1\n"
    assert (target / "owned-1.dist-info/RECORD").read_bytes() == (site / "owned-1.dist-info/RECORD").read_bytes()
    assert (target / "z3/lib/libz3.dylib").read_bytes() == b"admitted canonical library"
    assert not (target / omitted).exists()
    assert not (target / "injected.py").exists()
    assert not target.stat().st_mode & 0o222


def test_retained_pip_bytecode_record_works_with_unfiltered_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    site, target, graph = _recorded_site(tmp_path, ["owned/__pycache__/__init__.cpython-313.pyc"])

    def unfiltered_files(distribution: Distribution) -> list[PackagePath]:
        # CPython 3.11-3.13 metadata exposes RECORD entries even when absent;
        # 3.14 filters them. Exercise the supported older behavior on either host.
        record = distribution.read_text("RECORD")
        assert record is not None
        return [PackagePath(line.split(",", 1)[0]) for line in record.splitlines()]

    monkeypatch.setattr(Distribution, "files", property(unfiltered_files))

    native_analyzer_view.build_analyzer_view(site, target, graph)

    assert (target / "owned/__init__.py").read_text() == "VALUE = 1\n"
    assert (target / "owned-1.dist-info/METADATA").is_file()
    assert not (target / "owned/__pycache__").exists()


@pytest.mark.parametrize(
    "missing",
    [
        "owned/__init__.py",
        "owned/data.json",
        "owned-1.dist-info/WHEEL",
        "semgrep/bin/semgrep-core",
        "semgrep/bin/libs/libengine.dylib",
        "z3/lib/libz3.dylib",
        "z3/lib/libz3.9.0.dylib",
    ],
)
def test_preparation_omissions_do_not_hide_missing_member_dependencies(tmp_path: Path, missing: str) -> None:
    site, target, graph = _recorded_site(tmp_path, ["owned/__pycache__/cache.pyc", missing])
    if missing == "owned/__init__.py":
        (site / missing).unlink()

    with pytest.raises(ValueError, match="recorded payload is missing"):
        native_analyzer_view.build_analyzer_view(site, target, graph)

    assert not target.exists()


def test_omitted_z3_alias_requires_recorded_canonical_library(tmp_path: Path) -> None:
    site, target, graph = _recorded_site(tmp_path, ["z3/lib/libz3.5.1.dylib"])
    library = site / "z3/lib/libz3.dylib"
    library.parent.mkdir(parents=True)
    library.write_bytes(b"unrecorded canonical library")

    with pytest.raises(ValueError, match="recorded payload is missing"):
        native_analyzer_view.build_analyzer_view(site, target, graph)

    assert not target.exists()


def test_omitted_bytecode_record_cannot_hide_a_dangling_symlink(tmp_path: Path) -> None:
    site, target, graph = _recorded_site(tmp_path, ["owned/cache.pyc"])
    (site / "owned/cache.pyc").symlink_to(tmp_path / "missing.pyc")

    with pytest.raises(ValueError, match="indirection"):
        native_analyzer_view.build_analyzer_view(site, target, graph)

    assert not target.exists()


@pytest.mark.parametrize("entry_kind", ["directory", "fifo"])
def test_omission_requires_an_absent_file_not_a_present_nonregular_entry(tmp_path: Path, entry_kind: str) -> None:
    site, target, graph = _recorded_site(tmp_path, ["owned/cache.pyc"])
    entry = site / "owned/cache.pyc"
    if entry_kind == "directory":
        entry.mkdir()
    else:
        os.mkfifo(entry)

    with pytest.raises(ValueError, match="recorded payload is missing"):
        native_analyzer_view.build_analyzer_view(site, target, graph)

    assert not target.exists()


def test_retained_record_still_requires_exact_member_version(tmp_path: Path) -> None:
    site, target, graph = _recorded_site(tmp_path, ["owned/cache.pyc"])
    graph["installed"][0]["version"] = "2"

    with pytest.raises(ValueError, match="distribution identity differs"):
        native_analyzer_view.build_analyzer_view(site, target, graph)

    assert not target.exists()


def test_retained_record_still_rejects_duplicate_file_ownership(tmp_path: Path) -> None:
    site, target, graph = _recorded_site(tmp_path, ["owned/cache.pyc"])
    info = site / "other-1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: other\nVersion: 1\n")
    (info / "RECORD").write_text("owned/__init__.py,,\nother-1.dist-info/METADATA,,\n")
    graph["installed"].append({"name": "other", "version": "1", "origin": "analyzer"})

    with pytest.raises(ValueError, match="ownership is ambiguous"):
        native_analyzer_view.build_analyzer_view(site, target, graph)

    assert not target.exists()


def test_retained_record_still_rejects_hard_linked_payload(tmp_path: Path) -> None:
    site, target, graph = _recorded_site(tmp_path, ["owned/cache.pyc"])
    os.link(site / "owned/__init__.py", tmp_path / "duplicate.py")

    with pytest.raises(ValueError, match="indirection"):
        native_analyzer_view.build_analyzer_view(site, target, graph)
