"""Maintainer Git pin, bounded source and Apple-only linkage contract."""

import importlib.util
import io
import tarfile
from pathlib import Path

import pytest


@pytest.fixture
def builder():
    source = Path(__file__).resolve().parents[2] / "scripts/build_macos_managed_git.py"
    spec = importlib.util.spec_from_file_location("managed_git_builder", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_official_archive_pin_rejects_substitution(builder, tmp_path):
    archive = tmp_path / "git.tar.xz"
    archive.write_bytes(b"substituted release")
    with pytest.raises(ValueError, match="pin"):
        builder.validate_archive(archive)
    assert builder.UPSTREAM_COMMIT == "94f057755b7941b321fd11fec1b2e3ca5313a4e0"
    assert builder.ARCHIVE_SHA256 == "f689162364c10de79ef89aa8dbf48731eb057e34edbbd20aca510ce0154681a3"


@pytest.mark.parametrize("name,kind", [("../escape", tarfile.REGTYPE), ("git-2.54.0/link", tarfile.SYMTYPE)])
def test_extraction_rejects_paths_and_links(builder, tmp_path, name, kind):
    archive = tmp_path / "unsafe.tar.xz"
    with tarfile.open(archive, "w:xz") as stream:
        item = tarfile.TarInfo(name)
        item.type = kind
        item.size = 1 if kind == tarfile.REGTYPE else 0
        item.linkname = "/host/input"
        stream.addfile(item, io.BytesIO(b"x") if item.size else None)
    with pytest.raises(ValueError, match="source"):
        builder.extract_source(archive, tmp_path / "source")


@pytest.mark.parametrize("dependency", ["/opt/homebrew/lib/libz.dylib", "@rpath/libcrypto.dylib", "/tmp/lib.dylib"])
def test_static_closure_rejects_external_libraries(builder, dependency):
    listing = f"/artifact/git:\n\t{dependency} (compatibility version 1.0.0, current version 1.0.0)\n"
    with pytest.raises(ValueError, match="closure"):
        builder.apple_dependencies(listing)


def test_build_disables_transports_helpers_and_package_discovery(builder, tmp_path):
    command, environment = builder.make_invocation(tmp_path, Path("/sdk"), Path("/usr/bin/clang"), jobs=2)
    assert command[:3] == ["/usr/bin/make", "-j2", "git"]
    for name in (
        "NO_CURL",
        "NO_OPENSSL",
        "NO_EXPAT",
        "NO_PERL",
        "NO_PYTHON",
        "NO_GETTEXT",
        "NO_TCLTK",
        "NO_UNIX_SOCKETS",
        "NO_HOMEBREW",
        "NO_FINK",
        "NO_DARWIN_PORTS",
    ):
        assert f"{name}=YesPlease" in command
    assert environment["PATH"] == "/usr/bin:/bin:/usr/sbin:/sbin"
    assert environment["HOME"] == str(tmp_path)
    assert not any("signing" in name.lower() or "token" in name.lower() for name in environment)
    assert builder.BUILD_TIMEOUT_SECONDS <= 600
