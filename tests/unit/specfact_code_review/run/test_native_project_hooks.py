"""Project backends execute separately from managers on disposable sources."""

from pathlib import Path

import pytest

from specfact_code_review.run import native_project_hatch, native_project_hooks
from specfact_code_review.run.runtime_models import ProjectRuntimeError


def test_editable_requirements_are_discovered_from_the_actual_backend(tmp_path):
    project, output, temporary, dependencies = [tmp_path / name for name in ("project", "output", "temporary", "deps")]
    for root in (project, output, temporary, dependencies):
        root.mkdir()
    (project / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="customer_backend"\nbackend-path=["."]\n'
    )
    (project / "customer_backend.py").write_text(
        'def get_requires_for_build_editable(config_settings=None):\n    return ["editables~=0.3"]\n'
        'def get_requires_for_build_wheel(config_settings=None):\n    return ["wheel"]\n'
    )
    assert native_project_hooks.execute_hook(
        project, output, temporary, dependencies, operation="editable-requirements"
    ) == {"requirements": ["editables~=0.3"]}


def test_backend_runs_on_disposable_copy_and_requests_build_dependencies(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="fixture_backend"\nbackend-path=["."]\n'
    )
    (project / "fixture_backend.py").write_text(
        "from pathlib import Path\n"
        "def get_requires_for_build_wheel(config_settings=None):\n"
        '    Path("hook-marker").write_text("disposable")\n'
        '    return ["idna>=3"]\n'
    )
    output, temporary, dependencies = tmp_path / "output", tmp_path / "temporary", tmp_path / "dependencies"
    for path in (output, temporary, dependencies):
        path.mkdir()
    result = native_project_hooks.execute_hook(project, output, temporary, dependencies, operation="requirements")
    assert result["requirements"] == ["idna>=3"]
    assert not (project / "hook-marker").exists()
    assert (temporary / "source/hook-marker").read_text() == "disposable"


def test_writable_hook_copy_preserves_executable_status(tmp_path: Path) -> None:
    project, output, temporary, dependencies = [tmp_path / name for name in ("project", "output", "temporary", "deps")]
    for root in (project, output, temporary, dependencies):
        root.mkdir()
    (project / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="mode_backend"\nbackend-path=["."]\n'
    )
    (project / "mode_backend.py").write_text(
        'from pathlib import Path\ndef get_requires_for_build_wheel(config_settings=None):\n    assert Path("script.py").stat().st_mode & 0o111\n    return []\n'
    )
    (project / "script.py").write_text("pass\n")
    (project / "script.py").chmod(0o500)
    assert native_project_hooks.execute_hook(project, output, temporary, dependencies, operation="requirements") == {
        "requirements": []
    }


def test_backend_path_cannot_import_host_code(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="fixture"\nbackend-path=["../outside"]\n'
    )
    with pytest.raises(ProjectRuntimeError, match="project_native_backend_path_escape"):
        native_project_hooks.build_configuration(tmp_path)


def test_backend_path_requires_a_verifiable_module_file(tmp_path: Path) -> None:
    project, output, temporary, dependencies = [tmp_path / name for name in ("project", "output", "temporary", "deps")]
    for root in (project, output, temporary, dependencies):
        root.mkdir()
    (project / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="namespace_backend"\nbackend-path=["."]\n'
    )
    (project / "namespace_backend").mkdir()
    with pytest.raises(ProjectRuntimeError, match="project_native_backend_path_escape"):
        native_project_hooks.execute_hook(project, output, temporary, dependencies, operation="requirements")


def test_workspace_hook_preserves_ancestor_vcs_and_member_directory(tmp_path: Path) -> None:
    project, output, temporary, dependencies = [tmp_path / name for name in ("project", "output", "temporary", "deps")]
    for root in (project, output, temporary, dependencies):
        root.mkdir()
    (project / ".git").mkdir()
    (project / ".git/HEAD").write_text("ref: refs/heads/fixture\n")
    member = project / "backend"
    member.mkdir()
    (member / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="workspace_backend"\nbackend-path=["."]\n'
    )
    (member / "workspace_backend.py").write_text(
        "from pathlib import Path\ndef get_requires_for_build_wheel(config_settings=None):\n"
        '    assert Path.cwd().name == "backend"\n'
        '    assert Path("../.git/HEAD").read_text() == "ref: refs/heads/fixture\\n"\n'
        "    return []\n"
    )
    assert native_project_hooks.execute_hook(
        project, output, temporary, dependencies, operation="requirements", project_subdirectory="backend"
    ) == {"requirements": []}


@pytest.mark.parametrize("selected", ["../outside", "/private/tmp", "backend/../backend", "missing"])
def test_workspace_hook_rejects_uncontained_member(tmp_path: Path, selected: str) -> None:
    project, output, temporary, dependencies = [tmp_path / name for name in ("project", "output", "temporary", "deps")]
    for root in (project, output, temporary, dependencies):
        root.mkdir()
    with pytest.raises(ProjectRuntimeError, match="project_native_build_subdirectory_invalid"):
        native_project_hooks.execute_hook(
            project, output, temporary, dependencies, operation="requirements", project_subdirectory=selected
        )


def test_declared_requires_without_backend_uses_pip_default(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires=["setuptools>=40.8"]\n')
    assert native_project_hooks.build_configuration(tmp_path)["build-backend"] == "setuptools.build_meta:__legacy__"


def test_backend_receives_declared_dependency_even_when_capsule_module_is_loaded(tmp_path: Path) -> None:
    import packaging

    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="fixture_backend"\nbackend-path=["."]\n'
    )
    (project / "fixture_backend.py").write_text(
        "import packaging\n"
        "def get_requires_for_build_wheel(config_settings=None):\n"
        "    assert packaging.__version__ == 'declared-fixture'\n"
        "    return []\n"
    )
    output, temporary, dependencies = tmp_path / "output", tmp_path / "temporary", tmp_path / "dependencies"
    for path in (output, temporary, dependencies):
        path.mkdir()
    (dependencies / "packaging").mkdir()
    (dependencies / "packaging/__init__.py").write_text("__version__ = 'declared-fixture'\n")
    native_project_hooks.execute_hook(project, output, temporary, dependencies, operation="requirements")
    assert packaging.__version__ != "declared-fixture"


def test_build_isolation_preserves_the_worker_main_module(tmp_path: Path, monkeypatch) -> None:
    import sys
    from types import ModuleType

    main = ModuleType("__main__")
    main.__file__ = "/capsule/site-packages/specfact_code_review/run/native_project_hooks.py"
    monkeypatch.setitem(sys.modules, "__main__", main)
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[build-system]\nrequires=[]\nbuild-backend="fixture_backend"\nbackend-path=["."]\n'
    )
    (project / "fixture_backend.py").write_text(
        "import sys\ndef get_requires_for_build_wheel(config_settings=None):\n"
        "    assert sys.modules['__main__'].__name__=='__main__'\n    return []\n"
    )
    output, temporary, dependencies = (tmp_path / name for name in ("output", "temporary", "dependencies"))
    for path in (output, temporary, dependencies):
        path.mkdir()
    assert native_project_hooks.execute_hook(project, output, temporary, dependencies, operation="requirements") == {
        "requirements": []
    }


def test_hatch_hook_keeps_original_admitted_inputs_separate_from_writable_source(tmp_path, monkeypatch):
    project, output, temporary, dependencies = (tmp_path / name for name in ("project", "output", "temporary", "deps"))
    for root in (project, output, temporary, dependencies):
        root.mkdir()
    wheelhouse = project / "wheelhouse"
    wheelhouse.mkdir()
    wheel = wheelhouse / "fixture.whl"
    wheel.write_bytes(b"original admitted wheel")
    wheel.chmod(0o400)
    wheelhouse.chmod(0o500)
    calls = []

    def execute(source, _output, _temporary, _capsule, *, operation, input_project=None):
        calls.append((source, input_project, operation))
        return {"status": "COMPLETE"}

    monkeypatch.setattr(native_project_hatch, "execute", execute)
    assert native_project_hooks.execute_hook(project, output, temporary, dependencies, operation="hatch.install") == {
        "status": "COMPLETE"
    }
    assert calls == [(temporary / "source", project, "hatch.install")]
    assert wheel.read_bytes() == b"original admitted wheel"
    assert wheel.stat().st_mode & 0o777 == 0o400
    assert wheelhouse.stat().st_mode & 0o777 == 0o500


@pytest.mark.parametrize("code,recorded", [(2, 2), (0, 0), (None, 0), ("private-exit-secret", None)])
def test_hook_main_records_untrusted_system_exit_without_claiming_success(tmp_path, monkeypatch, code, recorded):
    import json
    from contextlib import nullcontext

    from specfact_code_review.run import native_managed_process, native_python_environment

    project, output, temporary, capsule = (tmp_path / name for name in ("project", "output", "temporary", "capsule"))
    for path in (project, output, temporary, capsule):
        path.mkdir()
    (project / ".specfact-hook.json").write_text(json.dumps({"operation": "hatch.install", "extras": []}))
    monkeypatch.setattr(native_python_environment, "activate", lambda _path: None)
    monkeypatch.setattr(native_managed_process, "installed_subprocess", lambda *_args: nullcontext())
    monkeypatch.setattr(
        native_project_hooks.sys, "argv", ["hook", str(capsule), str(project), str(output), str(temporary)]
    )

    def execute(*_args, **_kwargs):
        raise SystemExit(code)

    monkeypatch.setattr(native_project_hooks, "execute_hook", execute)
    for key in ("HOME", "TMPDIR", "XDG_CACHE_HOME"):
        monkeypatch.setenv(key, native_project_hooks.os.environ.get(key, ""))
    assert native_project_hooks.main() == 74
    receipt = json.loads((output / "preparation-error.json").read_text())
    assert receipt["origin"] == "project"
    assert receipt["exit_code"] == recorded
    assert receipt["diagnostic"] == "project_native_build_hook_exit:" + (
        str(recorded) if recorded is not None else "non_integer"
    )
    assert "private-exit-secret" not in json.dumps(receipt)
    assert not (output / "hook-result.json").exists()
