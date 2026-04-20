"""Tests for shared code-import path discovery and progress accounting."""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_project.analyzers.code_analyzer import CodeAnalyzer
from specfact_project.import_cmd.commands import _count_python_files


def _discover_code_files(*args, **kwargs):
    module = importlib.import_module("specfact_project.utils.import_path_policy")
    return module.discover_code_files(*args, **kwargs)


def test_discover_code_files_prunes_default_ignored_dirs_and_specfactignore(tmp_path: Path) -> None:
    """Discovery should exclude heavyweight defaults and repo-local ignore patterns before traversal."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "real.py").write_text("class RealFeature:\n    pass\n", encoding="utf-8")

    ignored_paths = [
        tmp_path / ".venv" / "lib" / "site-packages" / "noise.py",
        tmp_path / ".hidden" / "skip.py",
        tmp_path / "build" / "generated.py",
        tmp_path / ".specfact" / "cache" / "ignored.py",
        tmp_path / "custom_ignore" / "custom.py",
    ]
    for path in ignored_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("class Noise:\n    pass\n", encoding="utf-8")

    ignore_file = tmp_path / ".specfact" / ".specfactignore"
    ignore_file.parent.mkdir(parents=True, exist_ok=True)
    ignore_file.write_text("custom_ignore/\n", encoding="utf-8")

    result = _discover_code_files(tmp_path, extensions={".py"})

    assert [path.relative_to(tmp_path).as_posix() for path in result.files] == ["src/real.py"]
    assert _count_python_files(tmp_path) == 1


def test_discover_code_files_warns_for_heavy_ignored_and_large_repo(tmp_path: Path) -> None:
    """Discovery should warn when ignored artifact trees or filtered repo size look unusually large."""
    for idx in range(3):
        path = tmp_path / "src" / f"feature_{idx}.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"class Feature{idx}:\n    pass\n", encoding="utf-8")

    heavy_root = tmp_path / "node_modules"
    for idx in range(3):
        subtree = heavy_root / f"pkg_{idx}" / "nested.py"
        subtree.parent.mkdir(parents=True, exist_ok=True)
        subtree.write_text("class NodeModuleNoise:\n    pass\n", encoding="utf-8")

    result = _discover_code_files(
        tmp_path,
        extensions={".py"},
        heavy_ignored_entry_threshold=2,
        large_repo_file_threshold=2,
    )

    assert len(result.files) == 3
    assert any("node_modules" in warning for warning in result.warnings)
    assert any("Repository size may materially extend import duration" in warning for warning in result.warnings)


class _CapturingProgress:
    """Tiny Progress stub to capture task totals without rendering Rich output."""

    last_instance: _CapturingProgress | None = None

    def __init__(self, *args, **kwargs) -> None:
        _ = args, kwargs
        self.tasks: list[SimpleNamespace] = []
        _CapturingProgress.last_instance = self

    def __enter__(self) -> _CapturingProgress:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        _ = exc_type, exc, tb
        return False

    def add_task(self, description: str, total: int | None = None):
        task = SimpleNamespace(description=description, initial_description=description, total=total, completed=0)
        self.tasks.append(task)
        return len(self.tasks) - 1

    def update(self, task_id: int, **kwargs) -> None:
        task = self.tasks[task_id]
        for key, value in kwargs.items():
            setattr(task, key, value)

    def remove_task(self, task_id: int) -> None:
        _ = task_id


def test_code_analyzer_progress_total_uses_filtered_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Phase 3 progress total should match analyzable files, not raw discovered files."""
    (tmp_path / "src" / "real.py").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "real.py").write_text("class RealFeature:\n    pass\n", encoding="utf-8")
    (tmp_path / ".venv" / "lib" / "site-packages").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".venv" / "lib" / "site-packages" / "ghost.py").write_text(
        "class GhostFeature:\n    pass\n",
        encoding="utf-8",
    )

    monkeypatch.setattr("specfact_project.analyzers.code_analyzer.Progress", _CapturingProgress)
    monkeypatch.setattr(CodeAnalyzer, "_analyze_commit_history", lambda self: None)
    monkeypatch.setattr(CodeAnalyzer, "_enhance_features_with_dependencies", lambda self: None)
    monkeypatch.setattr(CodeAnalyzer, "_extract_technology_stack_from_dependencies", lambda self: [])

    analyzer = CodeAnalyzer(tmp_path, confidence_threshold=0.0)
    analyzer.analyze()

    progress = _CapturingProgress.last_instance
    assert progress is not None
    phase3 = next(task for task in progress.tasks if "Phase 3" in task.initial_description)
    assert phase3.total == 1
