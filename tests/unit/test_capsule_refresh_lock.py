"""Runtime lock generation verifies descriptor metadata against authenticated wheels."""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def refresh_api() -> Any:
    path = (
        Path(__file__).parents[2]
        / "openspec/changes/code-review-capsule-customer-execution/runtime-build/refresh_lock.py"
    )
    spec = importlib.util.spec_from_file_location("capsule_refresh_lock", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wheel_fixture(root: Path, api: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    filename = "beartype-0.22.9-py3-none-any.whl"
    metadata = b"Metadata-Version: 2.4\nName: beartype\nVersion: 0.22.9\n"
    wheel = root / filename
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("beartype-0.22.9.dist-info/METADATA", metadata)
        archive.writestr("beartype-0.22.9.dist-info/WHEEL", "Wheel-Version: 1.0\nTag: py3-none-any\n")
        archive.writestr("beartype/__init__.py", "")
    digest = api._digest(wheel.read_bytes())
    monkeypatch.setattr(api, "_WHEEL_SHA256", digest)
    return {
        "filename": filename,
        "sha256": digest,
        "size": wheel.stat().st_size,
        "name": "beartype",
        "normalized_name": "beartype",
        "version": "0.22.9",
        "direct_specifier": "==0.22.9",
        "python_tag": "py3",
        "abi_tag": "none",
        "platform_tag": "any",
        "metadata_sha256": api._digest(metadata),
        "entry_points_sha256": api._digest(b""),
        "entry_points": [],
    }


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "normalized_name",
        "version",
        "direct_specifier",
        "size",
        "python_tag",
        "abi_tag",
        "platform_tag",
        "metadata_sha256",
        "entry_points_sha256",
    ],
)
def test_refresh_rejects_descriptor_drift_before_lock_write(
    refresh_api: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A correct archive hash cannot authorize unrelated descriptor identity fields."""
    descriptor = _wheel_fixture(tmp_path, refresh_api, monkeypatch)
    descriptor[field] = 1 if field == "size" else "incorrect"
    (tmp_path / "beartype-wheel-descriptor.json").write_text(json.dumps(descriptor))
    with pytest.raises(ValueError, match="descriptor"):
        refresh_api._component(tmp_path)


def test_refresh_accepts_descriptor_derived_from_verified_wheel(
    refresh_api: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid descriptors preserve the existing lock projection."""
    descriptor = _wheel_fixture(tmp_path, refresh_api, monkeypatch)
    (tmp_path / "beartype-wheel-descriptor.json").write_text(json.dumps(descriptor))
    component = refresh_api._component(tmp_path)
    assert (component["id"], component["version"], component["wheel_size"]) == (
        "beartype",
        "0.22.9",
        descriptor["size"],
    )
