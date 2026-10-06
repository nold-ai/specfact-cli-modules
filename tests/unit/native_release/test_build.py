import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.native_release import build


def test_native_build_refuses_ambiguous_designated_requirements(tmp_path, monkeypatch):
    monkeypatch.setattr(
        build.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout="# designated => first\n# designated => second\n", stderr=""),
    )
    output = tmp_path / "requirement"
    with pytest.raises(ValueError, match="unique"):
        build.requirement_file(tmp_path / "image", output)
    assert not output.exists()


def test_unsupported_abi_cannot_create_or_download_inputs(tmp_path):
    script = Path(__file__).resolve().parents[3] / "scripts/native_release/prepare-ci.sh"
    root = tmp_path / "input"
    result = subprocess.run(["/bin/bash", str(script), "cp314", str(root)], capture_output=True, check=False)
    assert result.returncode == 2
    assert not root.exists()
