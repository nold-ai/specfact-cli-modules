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
    smoke = steps["Runtime discovery smoke across package managers"]
    assert smoke.get("env", {}).get("UV_PYTHON") == "${{ matrix.python-version }}"
    command = shlex.split(smoke["run"].splitlines()[-1])
    assert command[command.index("--modules-repo") + 1] == "${GITHUB_WORKSPACE}/" + checkout["path"]
    assert command[command.index("--launcher") + 1 :: 2] == [
        "direct",
        "hatch-source",
        "pip-editable",
        "pipx",
        "uv-run",
        "uvx",
    ]


def _resolve_fixture(tmp_path: Path, repository: str | None, commit: str) -> subprocess.CompletedProcess[str]:
    lock = tmp_path / "specfact-cli/ci/runtime-smoke-fixture.lock.json"
    lock.parent.mkdir(parents=True)
    if repository is not None:
        lock.write_text(json.dumps({"repository": repository, "commit": commit}), encoding="utf-8")
    return _run_quality_python_step(tmp_path, "Resolve reviewed runtime smoke fixture")


def _run_quality_python_step(tmp_path: Path, name: str) -> subprocess.CompletedProcess[str]:
    step = next(step for step in _quality_steps() if step.get("name") == name)
    script = step["run"].removeprefix("python - <<'PY'\n").removesuffix("\nPY\n")
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={
            **os.environ,
            "GITHUB_OUTPUT": str(tmp_path / "output"),
            "GITHUB_ENV": str(tmp_path / "env"),
            "RUNNER_TEMP": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
    )


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
    process = _resolve_fixture(tmp_path, repository, commit)
    output = tmp_path / "output"
    assert (process.returncode == 0) == accepted, process.stderr
    if accepted:
        assert output.read_text(encoding="utf-8") == f"ref={commit}\n"
    else:
        assert not output.exists()


def test_quality_uses_core_lock_typer_before_hatch_bootstrap(tmp_path: Path) -> None:
    core = tmp_path / "specfact-cli"
    core.mkdir()
    (core / "uv.lock").write_text('[[package]]\nname = "typer"\nversion = "0.27.0"\n', encoding="utf-8")
    name = "Constrain Typer to the paired core lock"
    process = _run_quality_python_step(tmp_path, name)
    assert process.returncode == 0, process.stderr
    exported = dict(line.split("=", 1) for line in (tmp_path / "env").read_text(encoding="utf-8").splitlines())
    assert exported["PIP_CONSTRAINT"] == exported["UV_CONSTRAINT"]
    assert Path(exported["PIP_CONSTRAINT"]).read_text(encoding="utf-8") == "typer==0.27.0\n"
    steps = {step.get("name"): step for step in _quality_steps()}
    assert steps[name]["if"] == steps["Bootstrap hatch env"]["if"]
    assert list(steps).index(name) < list(steps).index("Bootstrap hatch env")


def test_smoke_fails_closed_when_paired_core_lacks_fixture_lock(tmp_path: Path) -> None:
    process = _resolve_fixture(tmp_path, None, "a" * 40)
    assert process.returncode != 0
    assert "Promote core first" in process.stderr
    assert not (tmp_path / "output").exists()
