"""Public portable runtime CLI surfaces and review option propagation."""

import json
from pathlib import Path

from typer.testing import CliRunner

from specfact_code_review.review.commands import app
from specfact_code_review.run import runner
from specfact_code_review.run.commands import _build_review_run_request
from specfact_code_review.run.runner import ReviewOptions


def test_runtime_inspect_is_read_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname="consumer"\n')
    result = CliRunner().invoke(app, ["review", "runtime", "inspect", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["manager"] == "pip"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["pyproject.toml"]


def test_review_help_exposes_project_handoff() -> None:
    result = CliRunner().invoke(app, ["review", "run", "--help"], env={"TERM": "dumb", "NO_COLOR": "1"})
    assert result.exit_code == 0
    assert "--project-config" in result.output
    assert "--project-runtime" in result.output


def test_review_request_carries_runtime_options(tmp_path: Path) -> None:
    config, descriptor = tmp_path / "review.toml", tmp_path / "project-runtime.json"
    request = _build_review_run_request([], {"project_config": config, "project_runtime": descriptor})
    assert request.project_config == config
    assert request.project_runtime == descriptor
    options = ReviewOptions(project_config=config, project_runtime=descriptor)
    assert options.project_runtime == descriptor


def test_customer_actions_source_layout_does_not_select_publisher(monkeypatch) -> None:

    marker = object()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "customer/project")
    monkeypatch.setattr(runner, "_official_installed_payload", lambda: (marker, ""))
    monkeypatch.setattr(
        runner, "_protected_candidate_payload", lambda: (_ for _ in ()).throw(AssertionError("publisher selected"))
    )
    assert runner._selected_module_payload().payload is marker
