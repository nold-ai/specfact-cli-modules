"""Worker fallbacks include only the selected member's dependency closure."""

from pathlib import Path

import pytest

from specfact_code_review.run.runtime_domains import member_dependency_graphs
from specfact_code_review.run.runtime_models import ProjectRuntimeError


def _distribution(root: Path, name: str, *, dependencies: tuple[str, ...] = ()) -> None:
    metadata = root / f"{name}-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n"
        + "".join(f"Requires-Dist: {dependency}\n" for dependency in dependencies)
    )
    (metadata / "top_level.txt").write_text(name + "\n")


@pytest.fixture(autouse=True)
def other_member_entries(tmp_path: Path) -> None:
    for name in ("basedpyright", "crosshair-tool", "pytest", "pytest-cov"):
        _distribution(tmp_path, name)


def test_member_graph_excludes_unrelated_analyzer_packages(tmp_path: Path) -> None:
    _distribution(tmp_path, "pylint", dependencies=("shared>=1",))
    _distribution(tmp_path, "shared")
    _distribution(tmp_path, "unrelated")
    graph = member_dependency_graphs({"installed": []}, tmp_path)["pylint"]
    assert graph["sealed_imports"] == ["pylint", "shared"]
    assert {row["name"] for row in graph["installed"]} == {"pylint", "shared"}


def test_project_distribution_replaces_compatible_tool_dependency(tmp_path: Path) -> None:
    _distribution(tmp_path, "pylint", dependencies=("shared>=1",))
    _distribution(tmp_path, "shared", dependencies=("unrelated>=1",))
    _distribution(tmp_path, "unrelated")
    target = {"installed": [{"metadata": {"name": "shared", "version": "2.0", "requires_dist": []}}]}
    graph = member_dependency_graphs(target, tmp_path)["pylint"]
    assert graph["sealed_imports"] == ["pylint"]
    assert next(row for row in graph["installed"] if row["name"] == "shared")["origin"] == "project"
    assert "unrelated" not in {row["name"] for row in graph["installed"]}


def test_missing_member_dependency_cannot_be_silently_omitted(tmp_path: Path) -> None:
    _distribution(tmp_path, "pylint", dependencies=("absent>=1",))
    with pytest.raises(ProjectRuntimeError, match="project_analyzer_dependency_missing:pylint:absent"):
        member_dependency_graphs({"installed": []}, tmp_path)
