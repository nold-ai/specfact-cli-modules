from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]


def _quality_steps() -> list[dict[str, Any]]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/pr-orchestrator.yml").read_text(encoding="utf-8"))
    return workflow["jobs"]["quality"]["steps"]


def test_quality_uses_reviewed_ruff_version() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = config["tool"]["hatch"]["envs"]["default"]["dependencies"]
    assert [dependency for dependency in dependencies if dependency.startswith("ruff")] == ["ruff==0.16.0"]


def test_smoke_uses_separate_reviewed_checkout() -> None:
    steps = {step.get("name"): step for step in _quality_steps()}
    checkout = steps["Checkout reviewed runtime smoke fixture"]["with"]
    assert checkout == {
        "repository": "nold-ai/specfact-cli-modules",
        "ref": "${{ steps.runtime-fixture.outputs.ref }}",
        "path": ".specfact/runtime-smoke-modules",
        "persist-credentials": False,
    }
    smoke = steps["Runtime discovery smoke across package managers"]["run"]
    command = shlex.split(smoke.splitlines()[-1])
    assert command[command.index("--modules-repo") + 1] == "${GITHUB_WORKSPACE}/" + checkout["path"]
    assert command[command.index("--launcher") + 1 :: 2] == [
        "direct",
        "hatch-source",
        "pip-editable",
        "pipx",
        "uv-run",
        "uvx",
    ]


@pytest.mark.parametrize(
    ("repository", "commit", "accepted"),
    [
        ("nold-ai/specfact-cli-modules", "a" * 40, True),
        ("example/other", "a" * 40, False),
        ("nold-ai/specfact-cli-modules", "dev", False),
    ],
)
def test_fixture_ref_requires_official_repository_and_commit(
    tmp_path: Path, repository: str, commit: str, accepted: bool
) -> None:
    lock = tmp_path / "specfact-cli/ci/runtime-smoke-fixture.lock.json"
    lock.parent.mkdir(parents=True)
    lock.write_text(json.dumps({"repository": repository, "commit": commit}), encoding="utf-8")
    output = tmp_path / "output"
    step = next(step for step in _quality_steps() if step.get("id") == "runtime-fixture")
    script = step["run"].removeprefix("python - <<'PY'\n").removesuffix("\nPY\n")
    process = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert (process.returncode == 0) == accepted, process.stderr
    if accepted:
        assert output.read_text(encoding="utf-8") == f"ref={commit}\n"
    else:
        assert not output.exists()
