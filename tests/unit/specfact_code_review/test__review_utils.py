from __future__ import annotations

from pathlib import Path

from specfact_code_review._review_utils import normalize_path_variants, python_source_paths_for_tools, tool_error


def test_normalize_path_variants_includes_relative_and_resolved_paths(tmp_path: Path) -> None:
    file_path = tmp_path / "nested" / "example.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("VALUE = 1\n", encoding="utf-8")

    variants = normalize_path_variants(file_path)

    assert str(file_path.resolve()) in variants
    assert file_path.resolve().as_posix() in variants


def test_python_source_paths_for_tools_keeps_py_and_pyi_suffixes(tmp_path: Path) -> None:
    py_file = tmp_path / "a.py"
    pyi_file = tmp_path / "b.pyi"
    yaml_file = tmp_path / "module-package.yaml"
    py_file.write_text("x = 1\n", encoding="utf-8")
    pyi_file.write_text("def f() -> None: ...\n", encoding="utf-8")
    yaml_file.write_text("name: t\n", encoding="utf-8")

    assert python_source_paths_for_tools([py_file, pyi_file, yaml_file]) == [py_file, pyi_file]


def test_tool_error_returns_review_finding_defaults(tmp_path: Path) -> None:
    file_path = tmp_path / "example.py"
    file_path.write_text("VALUE = 1\n", encoding="utf-8")

    finding = tool_error(
        tool="pytest",
        file_path=file_path,
        message="Coverage data missing",
    )

    assert finding.category == "tool_error"
    assert finding.severity == "error"
    assert finding.tool == "pytest"
    assert finding.rule == "tool_error"
    assert finding.file == str(file_path)
    assert finding.line == 1
    assert finding.message == "Coverage data missing"
