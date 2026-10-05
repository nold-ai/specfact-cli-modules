"""Pinned Hatch preparation consumes the actual selected project environment."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import native_project_hatch
from specfact_code_review.run.runtime_models import ProjectRuntimeError


def test_manager_request_rejects_unknown_or_escaping_configuration(tmp_path: Path):
    request = tmp_path / ".specfact-hatch.json"
    request.write_text(
        json.dumps({"schema": "native-hatch-request-v1", "environment": "../host", "groups": [], "extras": []})
    )
    with pytest.raises(ProjectRuntimeError, match="hatch_request"):
        native_project_hatch.read_request(tmp_path)


def test_manager_request_preserves_caller_selection(tmp_path: Path):
    selected = {
        "schema": "native-hatch-request-v1",
        "environment": "review",
        "groups": ["testing"],
        "extras": ["native"],
    }
    (tmp_path / ".specfact-hatch.json").write_text(json.dumps(selected))
    assert native_project_hatch.read_request(tmp_path) == selected


def test_description_keeps_root_build_out_of_index_acquisition(tmp_path: Path):
    environment = SimpleNamespace(
        all_dependencies=[f"customer-project @ {tmp_path.as_uri()}", "idna==3.10"],
        metadata=SimpleNamespace(name="customer-project"),
    )
    assert native_project_hatch.acquisition_requirements(environment, tmp_path) == ["idna==3.10"]


@pytest.mark.parametrize("name,relative", [("other-project", ""), ("customer-project", "/other")])
def test_description_cannot_admit_an_arbitrary_local_source(tmp_path: Path, name: str, relative: str):
    environment = SimpleNamespace(
        all_dependencies=[f"{name} @ {tmp_path.as_uri()}{relative}"],
        metadata=SimpleNamespace(name="customer-project"),
    )
    with pytest.raises(ProjectRuntimeError, match="dependency_source_unsupported"):
        native_project_hatch.acquisition_requirements(environment, tmp_path)


def test_workspace_keeps_local_members_out_of_network_acquisition(tmp_path: Path):
    member = tmp_path / "backend"
    member.mkdir()
    (member / "pyproject.toml").write_text('[project]\nname="backend"\nversion="1"\n')
    environment = SimpleNamespace(
        all_dependencies=[f"root @ {tmp_path.as_uri()}", f"backend @ {member.as_uri()}", "idna==3.10"],
        metadata=SimpleNamespace(name="root"),
        workspace=SimpleNamespace(
            members=[
                SimpleNamespace(
                    name="backend",
                    project=SimpleNamespace(location=member),
                    features=["extra"],
                )
            ]
        ),
    )
    assert native_project_hatch.acquisition_requirements(environment, tmp_path) == ["idna==3.10"]
    assert native_project_hatch.workspace_projects(environment, tmp_path) == [
        {"name": "backend", "path": "backend", "extras": ["extra"]},
    ]


def test_workspace_cannot_declare_source_outside_snapshot(tmp_path: Path):
    environment = SimpleNamespace(
        workspace=SimpleNamespace(
            members=[
                SimpleNamespace(
                    name="host",
                    project=SimpleNamespace(location=tmp_path.parent),
                    features=[],
                )
            ]
        )
    )
    with pytest.raises(ProjectRuntimeError, match="hatch_workspace_invalid"):
        native_project_hatch.workspace_projects(environment, tmp_path)


@pytest.mark.parametrize("path", ["../host", "/host", "missing", "."])
def test_controller_rejects_untrusted_workspace_paths(tmp_path: Path, path: str):
    with pytest.raises(ProjectRuntimeError, match="hatch_workspace_invalid"):
        native_project_hatch.validate_workspace(tmp_path, [{"name": "backend", "path": path, "extras": []}])


def test_uv_installer_uses_packaged_image_and_offline_wheelhouse_without_editing_project(tmp_path, monkeypatch):
    project, temporary, capsule = (tmp_path / name for name in ("project", "temporary", "capsule"))
    project.mkdir()
    temporary.mkdir()
    (project / "wheelhouse").mkdir()
    config = project / "hatch.toml"
    original = "[envs.default]\ninstaller = 'uv'\n"
    config.write_text(original)
    tool = capsule / "tools/uv"
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b"verified uv fixture")
    tool.chmod(0o555)
    environment = SimpleNamespace(use_uv=True, config={"installer": "uv"}, explicit_uv_path="", uv_path=None)
    monkeypatch.setattr(native_project_hatch.os, "environ", {})
    native_project_hatch.configure_installer(environment, project, temporary, capsule)
    assert environment.config["installer"] == "uv"
    assert environment.config["uv-path"] == str(tool)
    assert "explicit_uv_path" not in environment.__dict__ and "uv_path" not in environment.__dict__
    assert native_project_hatch.os.environ["UV_OFFLINE"] == "1"
    assert native_project_hatch.os.environ["UV_FIND_LINKS"] == str(project / "wheelhouse")
    assert config.read_text() == original


def test_hatch_uv_configuration_rejects_missing_or_writable_packaged_image(tmp_path):
    environment = SimpleNamespace(use_uv=True, config={"installer": "uv"})
    with pytest.raises(ProjectRuntimeError, match="uv_image_not_admitted"):
        native_project_hatch.configure_installer(environment, tmp_path, tmp_path, tmp_path)


def test_pip_installer_keeps_upstream_choice(tmp_path, monkeypatch):
    environment = SimpleNamespace(use_uv=False, config={"installer": "pip"})
    monkeypatch.setattr(native_project_hatch.os, "environ", {})
    native_project_hatch.configure_installer(environment, tmp_path, tmp_path, tmp_path)
    assert environment.config == {"installer": "pip"}


def test_internal_hatch_test_matrix_uses_current_abi_and_preserves_concrete_selection():
    abi = ".".join(map(str, native_project_hatch.sys.version_info[:2]))
    project = SimpleNamespace(
        config=SimpleNamespace(
            internal_matrices={
                "hatch-test": {
                    "envs": {
                        "hatch-test.py3.10": {"python": "3.10"},
                        f"hatch-test.py{abi}": {"python": abi},
                    }
                }
            },
            matrices={},
        )
    )
    assert native_project_hatch.environment_name(project, "hatch-test") == f"hatch-test.py{abi}"
    assert native_project_hatch.environment_name(project, "review") == "review"
    assert native_project_hatch.environment_name(project, "hatch-test.py3.10") == "hatch-test.py3.10"


@pytest.mark.parametrize(
    "members",
    [
        {"review.py3.10": {"python": "3.10"}},
        {"review.one": {}, "review.two": {}},
    ],
)
def test_matrix_root_requires_one_compatible_environment(members):
    project = SimpleNamespace(config=SimpleNamespace(internal_matrices={}, matrices={"review": {"envs": members}}))
    with pytest.raises(ProjectRuntimeError, match="hatch_matrix_selection_required"):
        native_project_hatch.environment_name(project, "review")


def test_hatch_install_binds_original_wheelhouse_not_disposable_source(tmp_path, monkeypatch):
    project, inputs, temporary, output, capsule = (
        tmp_path / name for name in ("source", "inputs", "temporary", "output", "capsule")
    )
    for root in (project, inputs, temporary, output, capsule):
        root.mkdir()
    (inputs / "wheelhouse").mkdir(mode=0o500)
    # The writable duplicate exists but is not an installer input.
    (project / "wheelhouse").mkdir()
    request = {"schema": native_project_hatch.SCHEMA, "environment": "default", "groups": [], "extras": []}
    (project / ".specfact-hatch.json").write_text(json.dumps(request))
    uv = capsule / "tools/uv"
    uv.parent.mkdir()
    uv.write_bytes(b"verified packaged uv")
    uv.chmod(0o555)
    prefix = temporary / "environment"
    site = (
        prefix
        / f"lib/python{native_project_hatch.sys.version_info.major}.{native_project_hatch.sys.version_info.minor}/site-packages"
    )
    site.mkdir(parents=True)
    settings = []
    environment = SimpleNamespace(
        use_uv=True, config={"installer": "uv"}, virtual_env_path=prefix, check_compatibility=lambda: None
    )

    def prepare(_environment, *, keep_env):
        assert keep_env is False
        settings.append(dict(native_project_hatch.os.environ))

    environment.app = SimpleNamespace(project=SimpleNamespace(prepare_environment=prepare))
    monkeypatch.setattr(native_project_hatch, "_environment", lambda *_args: environment)
    monkeypatch.setattr(native_project_hatch, "environment_inventory", lambda *_args: {})
    monkeypatch.setattr(native_project_hatch.os, "environ", {})
    result = native_project_hatch.execute(
        project, output, temporary, capsule, operation="hatch.install", input_project=inputs
    )
    assert result["status"] == "COMPLETE"
    assert settings[0]["UV_FIND_LINKS"] == settings[0]["PIP_FIND_LINKS"] == str(inputs / "wheelhouse")
    assert settings[0]["UV_CACHE_DIR"] == str(temporary / "uv-cache")
    assert settings[0]["UV_OFFLINE"] == settings[0]["UV_NO_INDEX"] == "1"
    assert environment.config["installer"] == "uv"
