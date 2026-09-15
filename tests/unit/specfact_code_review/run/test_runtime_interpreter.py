"""Project Python selection is independent of the controller ABI."""

from pathlib import Path

import pytest

from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_interpreter import select_environment


def test_python_version_file_is_selected_and_explicit_config_takes_precedence(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n")
    assert discover_project(tmp_path).python == "3.11"
    config = tmp_path / "review.toml"
    config.write_text('python="3.13"\n')
    assert discover_project(tmp_path, config_path=config).python == "3.13"


def test_python_selection_uses_matching_signed_worker(tmp_path: Path) -> None:

    (tmp_path / ".python-version").write_text("3.11\n")
    assert select_environment(discover_project(tmp_path), current="linux-x86_64-cp312") == "linux-x86_64-cp311"


def test_python_selection_rejects_conflicting_pin(tmp_path: Path) -> None:

    (tmp_path / ".python-version").write_text("3.11\n")
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python=">=3.12"\n')
    with pytest.raises(ValueError, match="project_python_incompatible"):
        select_environment(discover_project(tmp_path), current="linux-x86_64-cp312")


@pytest.mark.parametrize(
    ("declaration", "current", "expected"),
    [
        ('[project]\nrequires-python=">=3.13,<3.14"\n', "cp312", "cp313"),
        ('[tool.poetry.dependencies]\npython=">=3.12,<3.13"\n', "cp313", "cp312"),
    ],
)
def test_python_constraints_can_select_compatible_worker_without_a_pin(
    tmp_path: Path, declaration: str, current: str, expected: str
) -> None:
    (tmp_path / "pyproject.toml").write_text(declaration)
    assert (
        select_environment(discover_project(tmp_path), current=f"linux-x86_64-{current}") == f"linux-x86_64-{expected}"
    )


def test_poetry_constraint_preserves_ambiguous_worker_selection(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[tool.poetry.dependencies]\npython=">=3.11,<3.13"\n')
    with pytest.raises(ValueError, match="project_python_ambiguous"):
        select_environment(discover_project(tmp_path), current="linux-x86_64-cp313")
