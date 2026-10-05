"""Public portable runtime CLI surfaces and review option propagation."""

import json
from pathlib import Path

from typer.testing import CliRunner

from specfact_code_review.review.commands import app
from specfact_code_review.run import native_backend, runner, runtime_commands
from specfact_code_review.run.commands import _build_review_run_request
from specfact_code_review.run.runner import ReviewOptions


def test_runtime_inspect_is_read_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname="consumer"\n')
    result = CliRunner().invoke(app, ["review", "runtime", "inspect", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["manager"] == "pip"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["pyproject.toml"]


def test_runtime_inspect_json_reports_manager_choices(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname="unfamiliar"\n[tool.hatch.envs.review]\n')
    (tmp_path / "uv.lock").write_text("version = 1\n")

    result = CliRunner().invoke(app, ["review", "runtime", "inspect", "--json"])

    assert result.exit_code == 2
    diagnostic = json.loads(result.output)
    assert diagnostic["status"] == "incomplete"
    assert diagnostic["diagnostic"] == "project_manager_ambiguous"
    assert diagnostic["candidates"] == ["hatch", "uv"]
    assert diagnostic["required_fields"] == ["manager"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["pyproject.toml", "uv.lock"]


def test_explicit_configuration_resolves_json_inspection(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname="unfamiliar"\n[tool.hatch.envs.review]\n')
    (tmp_path / "uv.lock").write_text("version = 1\n")
    config = tmp_path / "review.toml"
    config.write_text('manager="hatch"\nenvironment="review"\n')

    result = CliRunner().invoke(app, ["review", "runtime", "inspect", "--json", "--project-config", str(config)])

    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert plan["manager"] == "hatch"
    assert plan["environment"] == "review"


def test_runtime_inspect_json_reports_test_dependency_choices(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="unfamiliar"\n[project.optional-dependencies]\ntest=[]\ntests=[]\n'
    )
    result = CliRunner().invoke(app, ["review", "runtime", "inspect", "--json"])
    assert result.exit_code == 2
    diagnostic = json.loads(result.output)
    assert diagnostic["candidates"] == ["extra:test", "extra:tests"]
    assert diagnostic["required_fields"] == ["groups", "extras"]


def test_runtime_inspect_json_does_not_guess_invalid_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project\n")

    result = CliRunner().invoke(app, ["review", "runtime", "inspect", "--json"])

    assert result.exit_code == 2
    diagnostic = json.loads(result.output)
    assert diagnostic["diagnostic"] == "project_config_invalid"
    assert diagnostic["candidates"] == []
    assert diagnostic["required_fields"] == []


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


def test_runtime_prepare_passes_exact_acquisition_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname="consumer"\n')
    runtime = object()
    prepared = type(
        "Prepared",
        (),
        {
            "descriptor_path": tmp_path / "runtime/project-runtime.json",
            "identity": "sha256:" + "a" * 64,
        },
    )()
    observed: dict[str, object] = {}

    monkeypatch.setattr(runtime_commands, "select_environment", lambda *_args, **_kwargs: "darwin-arm64-cp312")
    monkeypatch.setattr(runner, "_capsule_environment_id", lambda: "darwin-arm64-cp312")
    monkeypatch.setattr(runner, "_prepare_capsule_runtime", lambda **_kwargs: (runtime, ""))
    monkeypatch.setattr(runner, "_cleanup_capsule_runtime", lambda value: observed.setdefault("cleanup", value))

    def prepare(plan, **kwargs):
        observed["plan"] = plan
        observed.update(kwargs)
        return prepared

    monkeypatch.setattr(runtime_commands, "prepare_runtime", prepare)
    url = "https://ghcr.io/v2/nold-ai/project-runtime/blobs/sha256:fixture"

    result = CliRunner().invoke(
        app,
        ["review", "runtime", "prepare", "--json", "--acquisition-url", url],
    )

    assert result.exit_code == 0, result.output
    assert observed["runtime"] is runtime
    assert observed["offline"] is False
    assert observed["acquisition_url"] == url
    assert observed["cleanup"] is runtime


def test_runtime_prepare_selects_from_native_controller_environment(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nname="consumer"\nrequires-python=">=3.12,<3.13"\n')
    runtime = type("Runtime", (), {"environment_id": "darwin-arm64-cp312"})()
    prepared = type(
        "Prepared",
        (),
        {
            "descriptor_path": tmp_path / "runtime/project-runtime.json",
            "identity": "sha256:" + "a" * 64,
        },
    )()
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        native_backend,
        "select_runtime_backend",
        lambda: native_backend.BackendSelection("darwin-arm64", "darwin-arm64-cp312", ""),
    )
    monkeypatch.setattr(runner, "_capsule_environment_id", lambda: "linux-x86_64-cp312")
    monkeypatch.setattr(runner, "_prepare_capsule_runtime", lambda **kwargs: (runtime, ""))
    monkeypatch.setattr(runner, "_cleanup_capsule_runtime", lambda _value: None)

    def select(_plan, *, current: str) -> str:
        observed["current"] = current
        return "darwin-arm64-cp312"

    monkeypatch.setattr(runtime_commands, "select_environment", select)
    monkeypatch.setattr(runtime_commands, "prepare_runtime", lambda *_args, **_kwargs: prepared)

    result = CliRunner().invoke(app, ["review", "runtime", "prepare", "--json"])

    assert result.exit_code == 0, result.output
    assert observed["current"] == "darwin-arm64-cp312"
