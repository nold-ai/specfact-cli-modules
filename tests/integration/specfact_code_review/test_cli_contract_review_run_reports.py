"""Execute CLI contract scenarios that assert JSON report file contents."""

from __future__ import annotations

import functools
import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from specfact_code_review.review.commands import app


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "pyproject.toml").is_file() and (parent / "registry" / "index.json").is_file():
            return parent
    raise RuntimeError("cannot locate repository root from test file path")


REPO_ROOT = _repo_root()
SCENARIO_PATH = REPO_ROOT / "tests" / "cli-contracts" / "specfact-code-review-run.scenarios.yaml"
REQUIRED_TOOLS = ("ruff", "radon", "basedpyright", "pylint", "semgrep")
REPORT_PLACEHOLDER = "CONTRACT_TMP_REPORT.json"

runner = CliRunner()


@functools.cache
def _load_scenarios() -> dict:
    return yaml.safe_load(SCENARIO_PATH.read_text(encoding="utf-8"))


def _skip_if_tools_missing() -> None:
    missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"Missing required review tools: {', '.join(missing)}")


def _scenario_names_with_file_expectations() -> list[str]:
    data = _load_scenarios()
    names: list[str] = []
    for scenario in data.get("scenarios", []):
        expect = scenario.get("expect") or {}
        if expect.get("file_content_contains"):
            names.append(scenario["name"])
    return names


@pytest.mark.integration
@pytest.mark.parametrize("scenario_name", _scenario_names_with_file_expectations())
def test_cli_contract_review_run_json_report_file(
    tmp_path: Path, scenario_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _skip_if_tools_missing()
    monkeypatch.chdir(REPO_ROOT)
    data = _load_scenarios()
    scenario = next(s for s in data["scenarios"] if s["name"] == scenario_name)
    expect = scenario["expect"]
    fragments: list[str] = expect["file_content_contains"]

    out_path = tmp_path / f"{scenario_name}.json"
    argv: list[str] = []
    for arg in scenario["argv"]:
        argv.append(str(out_path) if arg == REPORT_PLACEHOLDER else arg)

    assert REPORT_PLACEHOLDER in scenario["argv"], "expected CONTRACT_TMP_REPORT.json placeholder in argv"

    result = runner.invoke(app, ["review", "run", *argv])

    assert result.exit_code == expect["exit_code"], result.output
    assert out_path.is_file(), f"expected JSON report at {out_path}"
    report_text = out_path.read_text(encoding="utf-8")
    for fragment in fragments:
        assert fragment in report_text, f"missing {fragment!r} in report for {scenario_name!r}"
