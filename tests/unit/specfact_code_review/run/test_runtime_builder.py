"""Runtime builder separates dependency acquisition from source and host state."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run.runtime_builder import builder_command, copy_project, prepare_runtime
from specfact_code_review.run.runtime_models import ProjectPlan, ProjectRuntimeError


def test_builder_mounts_source_copy_and_no_host_home(tmp_path: Path) -> None:
    runtime = SimpleNamespace(root=tmp_path / "capsule", interpreter="/opt/specfact/python/bin/python3")
    command = builder_command(runtime, staging=tmp_path / "staging", executable="/proc/self/fd/12")
    assert command[0] == "/proc/self/fd/12"
    assert "--clearenv" in command
    assert "--share-net" in command
    assert str(Path.home()) not in command
    assert str(tmp_path / "staging") in command
    assert "/opt/specfact/output/build_driver.py" in command


def test_copy_project_preserves_input_and_excludes_sidecars(tmp_path: Path) -> None:
    source, target = tmp_path / "source", tmp_path / "copy"
    source.mkdir()
    (source / "app.py").write_text("VALUE = 1\n")
    (source / ".venv").mkdir()
    (source / ".venv" / "secret").write_text("not part of source")
    copy_project(source, target)
    assert (target / "app.py").read_bytes() == (source / "app.py").read_bytes()
    assert not (target / ".venv").exists()


def test_copy_project_rejects_external_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "escape").symlink_to("/etc/passwd")
    with pytest.raises(ProjectRuntimeError, match="symlink"):
        copy_project(source, tmp_path / "copy")


def test_copy_project_supports_repository_local_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "cert.pem").write_text("test certificate fixture")
    (source / "cert-link.pem").symlink_to("cert.pem")
    copy_project(source, tmp_path / "copy")
    assert (tmp_path / "copy/cert-link.pem").read_text() == "test certificate fixture"


def test_builder_provides_vcs_metadata_tool_without_host_configuration(tmp_path: Path) -> None:
    runtime = SimpleNamespace(root=tmp_path / "capsule", interpreter="/opt/specfact/python/bin/python")
    command = builder_command(runtime, staging=tmp_path / "staging", executable="/proc/self/fd/12")
    assert "/opt/specfact/output/builder-tools/bin:/opt/specfact/python/bin:/usr/bin:/bin" in command
    assert "GIT_CONFIG_NOSYSTEM" in command


def test_python_patch_constraint_uses_signed_interpreter_version(tmp_path: Path) -> None:
    plan = ProjectPlan(tmp_path, manager="pip", requires_python=">=3.12.1,<3.13")
    runtime = SimpleNamespace(environment_id="linux-x86_64-cp312", identity="sha256:" + "a" * 64)
    with pytest.raises(ProjectRuntimeError, match="offline_cache_miss"):
        prepare_runtime(plan, runtime=runtime, cache_root=tmp_path / "cache", offline=True)
