"""Tests for the reusable Requirements evidence evaluator."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from specfact_requirements.requirements.evidence import (
    _materialize_git_index_snapshot,
    evaluate_requirements_evidence,
    write_requirements_evidence,
)


def _git(repo_root: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=repo_root, check=True, capture_output=True, text=True)


def _initialize_repository(repo_root: Path) -> None:
    _git(repo_root, "init")
    _git(repo_root, "config", "user.email", "evidence@example.test")
    _git(repo_root, "config", "user.name", "Evidence Test")
    source = repo_root / "openspec" / "changes" / "widget-evidence" / "specs" / "widgets" / "spec.md"
    source.parent.mkdir(parents=True)
    source.write_text("staged source\n", encoding="utf-8")
    linked_test = repo_root / "tests" / "unit" / "test_widget.py"
    linked_test.parent.mkdir(parents=True)
    linked_test.write_text("STAGED = True\n", encoding="utf-8")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "initial")


def test_evaluate_requirements_evidence_rejects_ambiguous_selection(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exactly one of --base-ref or --staged"):
        evaluate_requirements_evidence(tmp_path, base_ref="HEAD", staged=True)


def test_write_requirements_evidence_rejects_aliased_output_and_summary_paths(tmp_path: Path) -> None:
    output_path = tmp_path / "evidence" / "requirements-evidence.json"
    summary_path = output_path.parent / "temporary" / ".." / output_path.name

    with pytest.raises(ValueError, match="different destinations"):
        write_requirements_evidence(tmp_path, output_path, summary_path, base_ref="HEAD")

    assert not output_path.parent.exists()


def test_write_requirements_evidence_rejects_existing_hard_linked_destinations(tmp_path: Path) -> None:
    output_path = tmp_path / "requirements-evidence.json"
    summary_path = tmp_path / "requirements-evidence.md"
    previous_contents = b'{"verdict": "previous"}\n'
    output_path.write_bytes(previous_contents)
    os.link(output_path, summary_path)

    with pytest.raises(ValueError, match="different destinations"):
        write_requirements_evidence(tmp_path, output_path, summary_path, base_ref="HEAD")

    assert output_path.read_bytes() == previous_contents
    assert summary_path.read_bytes() == previous_contents


def test_staged_snapshot_excludes_unstaged_source_and_test_edits(tmp_path: Path) -> None:
    _initialize_repository(tmp_path)
    source = tmp_path / "openspec" / "changes" / "widget-evidence" / "specs" / "widgets" / "spec.md"
    linked_test = tmp_path / "tests" / "unit" / "test_widget.py"
    source.write_text("staged source update\n", encoding="utf-8")
    linked_test.write_text("STAGED = False\n", encoding="utf-8")
    _git(tmp_path, "add", source.relative_to(tmp_path).as_posix())
    source.write_text("unstaged source edit\n", encoding="utf-8")

    with _materialize_git_index_snapshot(tmp_path) as snapshot_root:
        assert (snapshot_root / source.relative_to(tmp_path)).read_text(encoding="utf-8") == "staged source update\n"
        assert (snapshot_root / linked_test.relative_to(tmp_path)).read_text(encoding="utf-8") == "STAGED = True\n"
