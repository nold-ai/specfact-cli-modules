"""Verify Project feature outcomes and code quality evidence from source."""

from pathlib import Path

import pytest
from git import Actor, Commit, Repo
from specfact_cli.utils import env_manager, optional_deps

from specfact_project.analyzers.code_analyzer import CodeAnalyzer


SERVICE_SOURCE = """\
from fastapi import APIRouter

router = APIRouter()

class WidgetService:
    \"\"\"Manage the widgets exposed by the widget API.\"\"\"

    @router.post("/widgets")
    def create_widget(self, names: list[str] = []) -> list[str]:
        return names

class HealthyService:
    \"\"\"Manage healthy services without shared defaults.\"\"\"

    def create_service(self, name: str) -> str:
        return name
"""


def test_project_feature_and_quality_evidence_without_semgrep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "services.py").write_text(SERVICE_SOURCE, encoding="utf-8")
    policy_dir = tmp_path / "tools" / "semgrep"
    policy_dir.mkdir(parents=True)
    (policy_dir / "feature-detection.yml").write_text("rules: []\n", encoding="utf-8")
    probes: list[str] = []

    def unavailable(_repo: Path, tool: str, _env: object) -> tuple[bool, str]:
        probes.append(tool)
        return False, f"{tool} is unavailable"

    monkeypatch.setattr(env_manager, "check_tool_in_env", unavailable)
    monkeypatch.delenv("TEST_MODE", raising=False)
    analyzer = CodeAnalyzer(tmp_path, confidence_threshold=0.0)
    result = analyzer.analyze()

    assert "semgrep" not in probes
    feature = next(item for item in result.features if "Widget" in item.title)
    healthy = next(item for item in result.features if "Healthy" in item.title)
    assert "Exposes API endpoints: POST /widgets" in feature.outcomes
    assert any("Mutable default argument" in item for item in feature.constraints)
    assert all("Mutable default argument" not in item for item in healthy.constraints)
    assert any("Legacy Semgrep" in item["reason"] for item in analyzer.get_plugin_status())


def test_scoped_analysis_preserves_history_dependencies_and_incremental_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "helpers.py").write_text("DEFAULT_LIMIT = 12\n", encoding="utf-8")
    (source / "services.py").write_text(
        '''from helpers import DEFAULT_LIMIT

class Feature001:
    """Manage available reports."""

    def get_report(self, limit: int = DEFAULT_LIMIT) -> int:
        """Return the current report limit."""
        return limit
''',
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("# supported stack\n\npython==3.12\npsycopg2\n", encoding="utf-8")
    (tmp_path / "unrelated.py").write_text(SERVICE_SOURCE, encoding="utf-8")
    history = Repo.init(tmp_path)
    history.index.add(["src/helpers.py", "src/services.py"])
    actor = Actor("Test User", "tester@example.com")
    tree = history.index.write_tree()
    first = Commit.create_from_tree(history, tree, "feat: start FEATURE-001", [], author=actor, committer=actor)
    last = Commit.create_from_tree(
        history, tree, "feat: finish FEATURE-001", [first], head=True, author=actor, committer=actor
    )
    updates: list[tuple[int, list[str]]] = []

    def capture_update(count: int, themes: list[str]) -> None:
        updates.append((count, themes))

    monkeypatch.setenv("TEST_MODE", "true")
    analyzer = CodeAnalyzer(
        tmp_path, confidence_threshold=0.0, entry_point=Path("src"), incremental_callback=capture_update
    )
    result = analyzer.analyze()

    assert result.metadata is not None
    assert result.metadata.analysis_scope == "partial"
    assert result.metadata.entry_point == "src"
    assert result.idea is not None
    assert result.idea.constraints is not None
    assert {"Python 3.12", "PostgreSQL database"} <= set(result.idea.constraints)
    assert len(result.features) == 1
    feature = result.features[0]
    assert analyzer.commit_bounds[feature.key] == (last.hexsha[:8], first.hexsha[:8])
    assert analyzer.dependency_graph.has_edge("src.services", "src.helpers")
    assert updates and updates[-1][0] == 1


@pytest.mark.parametrize("entry_point", [Path("missing"), Path("..")])
def test_analysis_rejects_invalid_scope(tmp_path: Path, entry_point: Path) -> None:
    with pytest.raises(ValueError, match=r"Entry point (does not exist|must be within repository)"):
        CodeAnalyzer(tmp_path, entry_point=entry_point)


@pytest.mark.parametrize("pyan,networkx", [(False, False), (False, True), (True, False), (True, True)])
def test_builtin_analysis_status_is_independent_of_optional_graph_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pyan: bool, networkx: bool
) -> None:
    monkeypatch.setattr(optional_deps, "check_cli_tool_available", lambda tool: (pyan and tool == "pyan3", ""))
    monkeypatch.setattr(optional_deps, "check_python_package_available", lambda name: networkx and name == "networkx")

    plugins = {item["name"]: item for item in CodeAnalyzer(tmp_path).get_plugin_status()}

    assert plugins["AST Analysis"]["enabled"] and plugins["AST Analysis"]["used"]
    assert "Built-in Python feature and quality checks" in plugins["AST Analysis"]["reason"]
    graph = plugins["Dependency Graph Analysis"]
    assert graph["enabled"] is (pyan and networkx)
    assert graph["used"] is graph["enabled"]


def test_sequential_keys_and_custom_title_preserve_source_features(tmp_path: Path) -> None:
    (tmp_path / "services.py").write_text(SERVICE_SOURCE, encoding="utf-8")

    plan = CodeAnalyzer(tmp_path, confidence_threshold=0.0, key_format="sequential", plan_name="widget_api").analyze()

    assert plan.idea is not None
    assert plan.idea.title == "Widget Api"
    assert len({item.key for item in plan.features}) == 2
    assert any("Exposes API endpoints: POST /widgets" in item.outcomes for item in plan.features)


def test_malformed_module_does_not_hide_async_functions(tmp_path: Path) -> None:
    (tmp_path / "services.py").write_text(
        SERVICE_SOURCE + "\nasync def await_widgets() -> None:\n    return None\n", encoding="utf-8"
    )
    (tmp_path / "broken.py").write_text("def incomplete(\n", encoding="utf-8")
    analyzer = CodeAnalyzer(tmp_path, confidence_threshold=0.0)

    plan = analyzer.analyze()

    assert analyzer.async_patterns["services"] == ["await_widgets"]
    assert len(plan.features) == 2
    assert any("Exposes API endpoints: POST /widgets" in item.outcomes for item in plan.features)


def test_route_evidence_belongs_to_its_owning_feature(tmp_path: Path) -> None:
    (tmp_path / "service.py").write_text(
        """\
from fastapi import APIRouter

api = APIRouter()

class Route:
    def get_name(self):
        return "route"

class Billing:
    @api.get("/bills")
    def get_bill(self):
        return "bill"
""",
        encoding="utf-8",
    )

    plan = CodeAnalyzer(tmp_path, confidence_threshold=0.0).analyze()

    by_title = {feature.title: feature for feature in plan.features}
    assert "Exposes API endpoints: GET /bills" in by_title["Billing"].outcomes
    assert all("Exposes API endpoints" not in outcome for outcome in by_title["Route"].outcomes)
