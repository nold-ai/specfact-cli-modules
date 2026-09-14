"""Per-analyzer dependency conflicts never silently substitute project versions."""

from pathlib import Path


def test_incompatible_dependency_identifies_only_affected_member(tmp_path: Path) -> None:
    from specfact_code_review.run.runtime_compatibility import analyzer_dependency_conflicts

    metadata = tmp_path / "pylint-4.0.7.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: pylint\nVersion: 4.0.7\nRequires-Dist: shared>=2\n"
    )
    inventory = {
        "installed": [{"metadata": {"name": "shared", "version": "1.0"}}],
        "environment": {"python_version": "3.12"},
    }
    conflicts = analyzer_dependency_conflicts(inventory, tmp_path)
    assert "shared" in conflicts["pylint"]
    assert ">=2" in conflicts["pylint"]
    assert "basedpyright" not in conflicts


def test_compatible_common_project_package_is_not_rejected(tmp_path: Path) -> None:
    from specfact_code_review.run.runtime_compatibility import analyzer_dependency_conflicts

    metadata = tmp_path / "pylint-4.0.7.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: pylint\nVersion: 4.0.7\nRequires-Dist: shared>=2\n"
    )
    inventory = {
        "installed": [
            {"metadata": {"name": "shared", "version": "2.1"}},
            {"metadata": {"name": "requests", "version": "2.32.4"}},
        ]
    }
    assert analyzer_dependency_conflicts(inventory, tmp_path) == {}
