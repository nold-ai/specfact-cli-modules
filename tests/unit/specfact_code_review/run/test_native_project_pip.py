"""Real pip wheel preparation and acquisition input boundaries."""

import base64
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from specfact_code_review.run import native_project_pip
from specfact_code_review.run.runtime_discovery import discover_project
from specfact_code_review.run.runtime_models import ProjectRuntimeError


def wheel(root: Path, *, name: str = "unfamiliar_dep", requires: tuple[str, ...] = ()) -> Path:
    path = root / f"{name}-1.0-py3-none-any.whl"
    metadata = f"Metadata-Version: 2.1\nName: {name.replace('_', '-')}\nVersion: 1.0\n" + "".join(
        f"Requires-Dist: {value}\n" for value in requires
    )
    files = {
        f"{name}/__init__.py": b"VALUE = 7\n",
        f"{name}-1.0.dist-info/METADATA": metadata.encode(),
        f"{name}-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nGenerator: fixture\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{name}-1.0.data/data/resource.txt": b"standard wheel data scheme\n",
    }
    records = []
    for member, payload in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
        records.append(f"{member},sha256={digest},{len(payload)}")
    records.append(f"{name}-1.0.dist-info/RECORD,,")
    files[f"{name}-1.0.dist-info/RECORD"] = ("\n".join(records) + "\n").encode()
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return path


def test_actual_offline_pip_installs_standard_wheel_layout_without_hooks(tmp_path: Path) -> None:
    wheelhouse = tmp_path / "wheels"
    wheelhouse.mkdir()
    archive = wheel(wheelhouse)
    manifest = {archive.name: hashlib.sha256(archive.read_bytes()).hexdigest()}
    output = tmp_path / "output"
    output.mkdir()
    # pip 26 installs a permanent audit hook. Production uses a fresh worker;
    # the maintainer fixture must likewise not modify pytest's import machinery.
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; import json,sys; "
            "from specfact_code_review.run.native_project_pip import install_wheels; "
            "install_wheels(Path(sys.argv[1]),Path(sys.argv[2]),json.loads(sys.argv[3]),expected_pip=None)",
            str(wheelhouse),
            str(output),
            json.dumps(manifest),
        ],
        env={**os.environ, "PYTHONPATH": str(Path(native_project_pip.__file__).parents[2])},
        check=True,
        capture_output=True,
    )
    assert (output / "site-packages/unfamiliar_dep/__init__.py").read_text() == "VALUE = 7\n"
    assert (output / "site-packages/resource.txt").read_text() == "standard wheel data scheme\n"
    assert not list(output.rglob("*.pyc"))


def test_prepared_inventory_uses_target_metadata_without_importing_package_code(tmp_path: Path) -> None:
    site = tmp_path / "site-packages"
    site.mkdir()
    sealed = tmp_path / "sealed"
    sealed.mkdir()
    metadata = site / "unfamiliar-1.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Metadata-Version: 2.1\nName: unfamiliar\nVersion: 1\nRequires-Dist: idna>=3\n")
    (site / "unfamiliar.py").write_text("raise RuntimeError('project code must not run')\n")
    result = native_project_pip.environment_inventory(site, sealed)
    assert result["installed"][0]["metadata"] == {"name": "unfamiliar", "version": "1", "requires_dist": ["idna>=3"]}
    assert result["environment"]["python_version"] == f"{sys.version_info.major}.{sys.version_info.minor}"


def test_modified_acquired_wheel_is_rejected_before_install(tmp_path: Path) -> None:
    archive = wheel(tmp_path)
    with pytest.raises(ProjectRuntimeError, match="project_native_wheel_digest_mismatch"):
        native_project_pip.install_wheels(tmp_path, tmp_path / "output", {archive.name: "0" * 64}, expected_pip=None)
    assert not (tmp_path / "output").exists()


def test_trusted_wheel_inspector_reads_actual_metadata(tmp_path: Path) -> None:
    archive = wheel(tmp_path)
    with zipfile.ZipFile(archive, "a") as contents:
        contents.writestr("unrelated_backend.py", "raise RuntimeError('must not import backend')\n")
    assert native_project_pip.inspect_wheel(archive, []) == []


def test_resolver_receives_local_root_wheel_for_self_referencing_extras(tmp_path: Path, monkeypatch) -> None:
    inputs = tmp_path / "inputs"
    (inputs / "wheels").mkdir(parents=True)
    local = wheel(inputs / "wheels")
    output = tmp_path / "output"
    output.mkdir()
    calls = []
    monkeypatch.setattr(native_project_pip, "_pip", lambda argv, expected: calls.append(argv))
    native_project_pip._acquire(
        {"schema": native_project_pip.SCHEMA, "requirements": ["unfamiliar-dep[test]"], "constraints": []},
        output,
        local_wheels=inputs / "wheels",
    )
    assert "unfamiliar-dep @ " + local.as_uri() in (output / "requirements.txt").read_text().splitlines()


@pytest.mark.parametrize("hashed", [False, True])
def test_actual_pip_resolves_workspace_chain_from_explicit_local_wheels_without_index(
    tmp_path: Path, hashed: bool
) -> None:
    local, output = tmp_path / "local wheels", tmp_path / "output"
    local.mkdir()
    output.mkdir()
    root = wheel(local, name="workspace_root", requires=("workspace-member==1.0",))
    member = wheel(local, name="workspace_member")
    requirement = "workspace-root==1.0" + (
        f" --hash=sha256:{hashlib.sha256(root.read_bytes()).hexdigest()}" if hashed else ""
    )
    process = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; import sys,pip; from specfact_code_review.run import native_project_pip as module; "
            "module.PIP_VERSION=pip.__version__; original=module._pip; "
            "module._pip=lambda argv,version: original([*argv,'--no-index'],version); "
            "module._acquire({'schema':module.SCHEMA,'requirements':[sys.argv[3]],'constraints':[]},Path(sys.argv[2]),local_wheels=Path(sys.argv[1]))",
            str(local),
            str(output),
            requirement,
        ],
        env={"PATH": os.defpath, "PYTHONPATH": str(Path(native_project_pip.__file__).parents[2])},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 0, process.stderr
    assert set(json.loads((output / "wheel-manifest.json").read_text())) == {root.name, member.name}


def test_acquisition_verifies_https_using_bundled_certificates(tmp_path: Path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(native_project_pip, "_pip", lambda arguments, expected: calls.append((arguments, expected)))
    native_project_pip._acquire(
        {"schema": native_project_pip.SCHEMA, "requirements": ["idna==3.10"], "constraints": []}, tmp_path
    )
    assert "--use-deprecated=legacy-certs" in calls[0][0]
    assert calls[0][1] == native_project_pip.PIP_VERSION


@pytest.mark.parametrize(
    "requirement",
    [
        "--index-url https://evil.test",
        "dep @ file:///private/secret",
        "dep @ https://example.com/dep.tar.gz",
        "../source",
        "git+https://example.com/repo.git",
        "dep\nother",
    ],
)
def test_acquisition_never_accepts_options_sources_or_sdist_hooks(requirement: str) -> None:
    with pytest.raises(ProjectRuntimeError, match="project_native_dependency_source_unsupported"):
        native_project_pip.validate_requirement(requirement)


def test_actual_project_requirements_constraints_groups_and_extras_are_selected(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="unfamiliar"\nversion="1"\ndependencies=["idna>=3"]\n'
        '[project.optional-dependencies]\ntesting=["pytest>=8"]\n'
        '[dependency-groups]\nbase=["coverage>=7"]\nreview=[{include-group="base"},"pytest-cov>=6"]\n'
    )
    (tmp_path / "requirements.txt").write_text("-r nested.txt\ncharset-normalizer>=3\n")
    (tmp_path / "nested.txt").write_text("certifi>=2025\n")
    (tmp_path / "constraints.txt").write_text("idna<4\n")
    config = tmp_path / "review.toml"
    config.write_text(
        'manager="pip"\ngroups=["review"]\nextras=["testing"]\nrequirements=["requirements.txt"]\nconstraints=["constraints.txt"]\n'
    )
    request = native_project_pip.dependency_request(discover_project(tmp_path, config_path=config))
    assert set(request["requirements"]) == {
        "idna>=3",
        "pytest>=8",
        "coverage>=7",
        "pytest-cov>=6",
        "certifi>=2025",
        "charset-normalizer>=3",
    }
    assert request["constraints"] == ["idna<4"]
    assert "unfamiliar" not in json.dumps(request)


def test_nested_requirements_cannot_escape_snapshot(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("-r ../secret.txt\n")
    with pytest.raises(ProjectRuntimeError, match=r"project_(native_requirements_path_unsupported|input_escape)"):
        native_project_pip.dependency_request(discover_project(tmp_path))


def test_recursive_group_expansion_stops_within_controller_budget(monkeypatch) -> None:
    groups: dict[str, list[str | dict[str, str]]] = {"leaf": ["idna>=3"]}
    for index in range(14):
        child = "leaf" if index == 0 else f"g{index - 1}"
        groups[f"g{index}"] = [{"include-group": child}, {"include-group": child}]
    monkeypatch.setattr(native_project_pip, "MAX_REQUIREMENTS", 128)
    with pytest.raises(ProjectRuntimeError, match="project_native_dependency_bounds_exceeded"):
        native_project_pip._group_requirements(groups, "g13")


def test_nested_constraint_includes_preserve_pip_requirement_mode(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("-cconstraints.txt\n")
    (tmp_path / "constraints.txt").write_text("idna<4\n-rextra.txt\n")
    (tmp_path / "extra.txt").write_text("idna>=3\n")
    request = native_project_pip.dependency_request(discover_project(tmp_path))
    assert request["requirements"] == ["idna>=3"]
    assert request["constraints"] == ["idna<4"]


def test_wheel_inspection_partitions_only_previously_admitted_git_sources(tmp_path):
    declaration = {
        "schema": "native-locked-git-v1",
        "name": "poetry-core",
        "version": "2.4.1",
        "url": "https://github.com/python-poetry/poetry-core.git",
        "reference": "HEAD",
        "commit": "b9663e42c808543377ae523611c4cfad68016f30",
        "subdirectory": "",
    }
    path = tmp_path / "root-1-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "root-1.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: root\nVersion: 1\n"
            "Requires-Dist: poetry-core @ git+https://github.com/python-poetry/poetry-core.git\nRequires-Dist: idna>=3\n",
        )
    assert native_project_pip.inspect_wheel(path, [], [declaration]) == ["idna>=3"]
    with pytest.raises(ProjectRuntimeError, match="dependency_source_unsupported"):
        native_project_pip.inspect_wheel(path, [], [{**declaration, "url": "https://github.com/other/repo.git"}])


def test_poetry_resolution_dispatch_uses_sealed_metadata_surface(tmp_path, monkeypatch):
    # The fixed worker entry point changes its process environment before exit.
    # This in-process dispatch fixture must restore the invoking test process.
    for key in ("HOME", "TMPDIR", "XDG_CACHE_HOME"):
        monkeypatch.setenv(key, os.environ.get(key, ""))
    from specfact_code_review.run import native_project_poetry

    project, output, temporary = (tmp_path / name for name in ("project", "output", "temporary"))
    for path in (project, output, temporary):
        path.mkdir()
    request = {"schema": "native-poetry-resolution-v1"}
    (project / "request.json").write_text(json.dumps(request))
    calls = []
    monkeypatch.setattr(native_project_poetry, "resolve_metadata", lambda *args: calls.append(args))
    monkeypatch.setattr(
        native_project_pip, "_acquire", lambda *args, **kwargs: pytest.fail("must use authentic Poetry solver")
    )
    monkeypatch.setattr(
        sys, "argv", ["worker", str(tmp_path / "capsule"), str(project), str(output), str(temporary), "acquire"]
    )
    assert native_project_pip.main() == 0
    assert calls == [(request, project, output, temporary)]
