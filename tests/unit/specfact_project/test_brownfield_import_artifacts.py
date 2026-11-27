"""Verify source tracking and relationship artifacts consumed by code import."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from specfact_cli.models.plan import Feature, PlanBundle, Product
from specfact_cli.models.source_tracking import SourceTracking
from specfact_cli.utils import optional_deps

from specfact_project.analyzers.graph_analyzer import GraphAnalyzer
from specfact_project.import_cmd import commands
from specfact_project.import_cmd.commands import _extract_relationships_and_graph, _update_source_tracking


@pytest.fixture(name="widget_source")
def make_widget_source(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp_path = tmp_path_factory.mktemp("widgets-source")
    implementation = tmp_path / "widgets.py"
    implementation.write_text("from storage import save\n\ndef create_widget():\n    return save()\n", encoding="utf-8")
    (tmp_path / "storage.py").write_text("def save():\n    return {'saved': True}\n", encoding="utf-8")
    (tmp_path / "test_widgets.py").write_text("from widgets import create_widget\n", encoding="utf-8")
    return implementation


@pytest.mark.parametrize("test_mode", ["true", "false"], ids=["sequential", "workers"])
def test_tracking_records_implementation_and_test_hashes(
    widget_source: Path, monkeypatch: pytest.MonkeyPatch, test_mode: str
) -> None:
    monkeypatch.setenv("TEST_MODE", test_mode)
    feature = Feature(
        key="FEATURE-WIDGETS",
        title="Widgets",
        source_tracking=SourceTracking(implementation_files=["widgets.py"], test_files=["test_widgets.py"]),
    )
    bundle = PlanBundle(
        idea=None,
        business=None,
        product=Product(themes=["Widgets"]),
        features=[feature],
        clarifications=None,
        metadata=None,
    )

    _update_source_tracking(bundle, widget_source.parent)

    tracking = bundle.features[0].source_tracking
    assert tracking is not None
    for file_path in (widget_source, widget_source.with_name("test_widgets.py")):
        assert tracking.file_hashes[str(file_path)] == hashlib.sha256(file_path.read_bytes()).hexdigest()


@pytest.mark.parametrize("include_tests", [False, True], ids=["production", "with-tests"])
def test_dependency_graph_respects_the_test_file_option(
    widget_source: Path, monkeypatch: pytest.MonkeyPatch, include_tests: bool
) -> None:
    monkeypatch.setattr(optional_deps, "check_cli_tool_available", lambda _: (True, None))
    monkeypatch.setattr(GraphAnalyzer, "extract_call_graph", lambda *_: {})
    repo = widget_source.parent

    relationships, graph = _extract_relationships_and_graph(
        repo, None, repo / "bundle", None, None, True, True, include_tests=include_tests
    )

    assert graph is not None
    assert graph["nodes"] == (3 if include_tests else 2)
    assert graph["edges"] == (2 if include_tests else 1)
    assert relationships["dependency_graph"] == graph


@pytest.mark.parametrize("confirmed", [False, True], ids=["declined", "confirmed"])
def test_interactive_constitution_bootstrap_follows_the_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, confirmed: bool
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.setattr(commands.runtime, "is_interactive", lambda: True)
    monkeypatch.setattr(commands.typer, "confirm", lambda _message, *, default: confirmed)

    commands._suggest_constitution_bootstrap(tmp_path)

    constitution = tmp_path / ".specify" / "memory" / "constitution.md"
    assert constitution.is_file() is confirmed
    if confirmed:
        assert "Constitution" in constitution.read_text(encoding="utf-8")


def test_noninteractive_import_prints_the_explicit_constitution_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.setattr(commands.runtime, "is_interactive", lambda: False)

    commands._suggest_constitution_bootstrap(tmp_path)

    assert "specfact spec sdd constitution bootstrap" in capsys.readouterr().out
    assert not (tmp_path / ".specify").exists()
