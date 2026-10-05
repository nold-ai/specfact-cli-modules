"""Relocatable Python metadata for real manager environment creation."""

import site
import sys
import sysconfig
from pathlib import Path

from specfact_code_review.run import native_python_environment


def test_python_library_metadata_uses_actual_capsule_root(tmp_path, monkeypatch):
    capsule = tmp_path / "capsule"
    (capsule / "python/lib").mkdir(parents=True)
    monkeypatch.setattr(sys, "base_prefix", str(capsule / "python"))
    values = {
        "LIBDIR": "/build-host/python/lib",
        "LIBPL": "/build-host/python/lib/config",
        "INCLUDEDIR": "/build-host/python/include",
        "build": "historical upstream build provenance",
    }
    monkeypatch.setattr(sysconfig, "get_config_vars", lambda: values)
    native_python_environment.activate(capsule)
    assert values["LIBDIR"] == str(capsule / "python/lib")
    assert values["LIBPL"] == str(capsule / "python/lib/config")
    assert values["INCLUDEDIR"] == str(capsule / "python/include")
    assert values["build"] == "historical upstream build provenance"


def test_private_prefix_updates_site_metadata_and_preserves_alias(tmp_path, monkeypatch):
    capsule, prefix = tmp_path / "capsule", tmp_path / "venv"
    (capsule / "python/lib").mkdir(parents=True)
    (prefix / "bin").mkdir(parents=True)
    monkeypatch.setattr(sys, "prefix", str(capsule / "python"))
    monkeypatch.setattr(sys, "exec_prefix", str(capsule / "python"))
    monkeypatch.setattr(sys, "executable", str(capsule / "python/bin/python3"))
    monkeypatch.setattr(sys, "base_prefix", str(capsule / "python"))
    monkeypatch.setattr(site, "PREFIXES", list(site.PREFIXES))
    monkeypatch.setattr(site, "ENABLE_USER_SITE", site.ENABLE_USER_SITE)
    monkeypatch.setattr(sysconfig, "get_config_vars", dict)
    native_python_environment.activate(capsule, prefix=str(prefix), alias="python3")
    assert sys.executable == str(prefix / "bin/python3")
    assert sys.prefix == str(prefix)
    assert [str(prefix)] == site.PREFIXES
    assert site.ENABLE_USER_SITE is False
    assert all(Path(path).is_relative_to(prefix) for path in site.getsitepackages())
