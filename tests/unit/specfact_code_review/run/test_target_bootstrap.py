"""Analyzer entry-point lookup rejects project-owned replacements."""

from pathlib import Path

import pytest

from specfact_code_review.run import target_bootstrap


def test_analyzer_entry_point_is_confined_to_verified_root(tmp_path: Path, monkeypatch) -> None:
    analyzers = tmp_path / "analyzers"
    analyzers.mkdir()
    (analyzers / "owned.py").write_text('raise AssertionError("lookup must not execute")\n')
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", analyzers)
    finder = target_bootstrap.AnalyzerFinder({"owned"})
    specification = finder.find_spec("owned")
    assert specification is not None
    assert specification.origin == str(analyzers / "owned.py")
    assert finder.find_spec("project_dependency") is None
    hostile = tmp_path / "hostile"
    hostile.mkdir()
    (hostile / "owned.py").write_text('raise AssertionError("must not execute")\n')
    with pytest.raises(ImportError, match="origin_mismatch"):
        finder.find_spec("owned", [str(hostile)])


def test_python_cli_keeps_code_separate_from_bootstrap(monkeypatch) -> None:
    from specfact_code_review.run.target_bootstrap import _project_python_command

    code = 'from __future__ import annotations\nprint("project code")'
    command, environment = _project_python_command(["-u", "-c", code])
    assert command[-3:] == ["-u", "-c", code]
    assert environment["SPECFACT_PROJECT_PYTHON"] == "1"
    assert environment["PYTHONPATH"] == "/opt/specfact/builtin/specfact_code_review/run"
