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


def test_member_fallback_rejects_unrelated_analyzer_imports(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "needed.py").write_text("VALUE = 1\n")
    (tmp_path / "unrelated.py").write_text("VALUE = 2\n")
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", tmp_path)
    finder = target_bootstrap.DomainFinder({"sealed_imports": ["needed"], "installed": []})
    assert finder.find_spec("needed") is not None
    assert finder.find_spec("unrelated") is None


def test_member_metadata_lookup_cannot_expand_explicit_target_inventory(tmp_path: Path, monkeypatch) -> None:
    from importlib.metadata import DistributionFinder

    metadata = tmp_path / "needed-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Metadata-Version: 2.1\nName: needed\nVersion: 1.0\n")
    monkeypatch.setattr(target_bootstrap, "ANALYZERS", tmp_path)
    finder = target_bootstrap.DomainFinder(
        {
            "sealed_imports": ["needed"],
            "installed": [{"name": "needed", "version": "1.0", "origin": "analyzer"}],
        }
    )
    context = DistributionFinder.Context(path=["/project-only"])
    assert not list(finder.find_distributions(context))
    default_context = DistributionFinder.Context(name="needed")
    assert [dist.version for dist in finder.find_distributions(default_context)] == ["1.0"]


def test_only_pytest_children_receive_the_pytest_dependency_domain(monkeypatch) -> None:
    from specfact_code_review.run.target_bootstrap import python_execution_domain

    monkeypatch.delenv("SPECFACT_TARGET_PYTEST", raising=False)
    assert python_execution_domain() == "project-python"
    monkeypatch.setenv("SPECFACT_TARGET_PYTEST", "1")
    assert python_execution_domain() == "pytest-observe"


@pytest.mark.parametrize(
    "arguments, option", [(["-I", "-c", "pass"], "-I"), (["-uS", "script"], "-S"), (["-E", "-m", "pytest"], "-E")]
)
def test_python_startup_cannot_bypass_runtime(arguments, option) -> None:
    with pytest.raises(RuntimeError, match=f"project_python_option_unsupported:{option}"):
        target_bootstrap._project_python_command(arguments)
