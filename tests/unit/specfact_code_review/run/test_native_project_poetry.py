"""Bounded Poetry selection and local wheel transport contracts."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import native_project_poetry as adapter
from specfact_code_review.run.runtime_models import ProjectRuntimeError


def request(project, **changes):
    value = {"schema": "native-poetry-request-v1", "groups": [], "extras": []}
    value.update(changes)
    (project / ".specfact-poetry.json").write_text(json.dumps(value))
    return value


@pytest.mark.parametrize(
    "changes", [{"groups": ["../host"]}, {"extras": ["x", "x"]}, {"host": True}, {"groups": "main"}]
)
def test_closed_request(tmp_path, changes):
    request(tmp_path, **changes)
    with pytest.raises(ProjectRuntimeError, match="poetry_request_invalid"):
        adapter.read_request(tmp_path)


def test_request_preserves_selection(tmp_path):
    selected = request(tmp_path, groups=["testing"], extras=["native"])
    assert adapter.read_request(tmp_path) == selected


def test_symlink_request_rejected(tmp_path):
    target = tmp_path / "target"
    target.write_text("{}")
    (tmp_path / ".specfact-poetry.json").symlink_to(target)
    with pytest.raises(ProjectRuntimeError, match="poetry_request_invalid"):
        adapter.read_request(tmp_path)


def test_selection_uses_upstream_default_and_normalized_names():
    package = SimpleNamespace(
        dependency_group_names=lambda **kwargs: {"main", "testing"}, extras={"native-feature": []}
    )
    assert adapter.selected_groups(package, {"groups": [], "extras": []}) == ["main", "testing"]
    assert adapter.selected_groups(package, {"groups": ["Testing"], "extras": ["native_feature"]}) == [
        "main",
        "testing",
    ]
    with pytest.raises(ProjectRuntimeError, match="selection_unknown"):
        adapter.selected_groups(package, {"groups": ["absent"], "extras": []})


@pytest.mark.parametrize("locked,fresh", [(False, True), (True, False)])
def test_lock_missing_or_stale_is_not_resolved(tmp_path, locked, fresh):
    (tmp_path / "poetry.lock").write_text("fixture")
    locker = SimpleNamespace(is_locked=lambda: locked, is_fresh=lambda: fresh)
    with pytest.raises(ProjectRuntimeError, match=r"lock_required|lock_stale"):
        adapter.validate_lock(tmp_path, locker)
    assert (tmp_path / "poetry.lock").read_text() == "fixture"


def test_requirements_follow_selected_operations_only():
    package = SimpleNamespace(name="idna", version="3.10", source_type=None)
    skipped = SimpleNamespace(skipped=True, package=SimpleNamespace(source_type="git"), job_type="install")
    selected = SimpleNamespace(skipped=False, package=package, job_type="install")
    assert adapter.acquisition_requirements([skipped, selected]) == ["idna==3.10"]
    package.source_type = "file"
    with pytest.raises(ProjectRuntimeError, match="dependency_source_unsupported"):
        adapter.acquisition_requirements([selected])


def test_local_wheel_requires_lock_filename_and_hash(tmp_path):
    wheel = tmp_path / "idna-3.10-py3-none-any.whl"
    wheel.write_bytes(b"wheel fixture")
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    package = SimpleNamespace(files=[{"file": wheel.name, "hash": "sha256:" + digest}])
    assert adapter.local_wheel(tmp_path, wheel.name, package) == wheel
    package.files[0]["hash"] = "sha256:" + "0" * 64
    with pytest.raises(ProjectRuntimeError, match="wheel_lock_mismatch"):
        adapter.local_wheel(tmp_path, wheel.name, package)
    with pytest.raises(ProjectRuntimeError, match="wheelhouse_invalid"):
        adapter.local_wheel(tmp_path, "../outside.whl", package)


def test_invalid_operation_does_not_import_manager(tmp_path):
    with pytest.raises(ProjectRuntimeError, match="operation_invalid"):
        adapter.execute(
            tmp_path, tmp_path / "output", tmp_path / "temporary", tmp_path / "capsule", operation="poetry.update"
        )


@pytest.mark.parametrize("relative", ["../host-site", "lib/site-packages"])
def test_private_installation_scheme_checked_before_install(tmp_path, relative):
    prefix = tmp_path / "private"
    prefix.mkdir()
    site = prefix / relative
    site.mkdir(parents=True)
    paths = {"purelib": str(site), "platlib": str(site), "scripts": str(prefix / "bin"), "data": str(prefix)}
    environment = SimpleNamespace(paths=paths, scheme_dict=paths)
    if relative.startswith(".."):
        with pytest.raises(ProjectRuntimeError, match="environment_outside_private_root"):
            adapter.private_site(environment, prefix)
    else:
        assert adapter.private_site(environment, prefix) == site
        environment.scheme_dict = {**paths, "scripts": str(tmp_path / "host-bin")}
        with pytest.raises(ProjectRuntimeError, match="environment_outside_private_root"):
            adapter.private_site(environment, prefix)


def test_split_site_scheme_is_explicitly_incomplete(tmp_path):
    environment = SimpleNamespace(paths={"purelib": str(tmp_path / "one"), "platlib": str(tmp_path / "two")})
    with pytest.raises(ProjectRuntimeError, match="split site"):
        adapter.private_site(environment, tmp_path)


def test_private_scheme_allows_readonly_interpreter_metadata(tmp_path):
    site = tmp_path / "lib/site-packages"
    site.mkdir(parents=True)
    paths = {
        "purelib": str(site),
        "platlib": str(site),
        "scripts": str(tmp_path / "bin"),
        "data": str(tmp_path),
        "include": str(tmp_path / "include"),
        "stdlib": "/sealed/python/lib",
        "userbase": "/denied/user",
        "fallbacks": [],
    }
    assert adapter.private_site(SimpleNamespace(paths=paths, scheme_dict=paths), tmp_path) == site


def test_description_never_installs_the_root_or_dependencies(tmp_path, monkeypatch):
    import sys
    from types import ModuleType

    request(tmp_path, groups=["testing"], extras=["native"])
    (tmp_path / "poetry.lock").write_text("unchanged lock fixture")
    poetry = SimpleNamespace(
        locker=SimpleNamespace(is_locked=lambda: True, is_fresh=lambda: True),
        package=SimpleNamespace(dependency_group_names=lambda **kw: {"main", "testing"}, extras={"native": []}),
        is_package_mode=True,
    )
    monkeypatch.setattr(adapter, "_project", lambda *args: poetry)
    module = ModuleType("poetry.utils.env")
    module.SystemEnv = lambda path: object()
    monkeypatch.setitem(sys.modules, "poetry.utils.env", module)
    calls = []

    def installer(poetry, env, groups, extras, executor):
        calls.append((groups, extras))
        selected = SimpleNamespace(
            skipped=False, job_type="install", package=SimpleNamespace(name="idna", version="3.10", source_type=None)
        )
        return SimpleNamespace(run=lambda: executor.execute([selected]))

    monkeypatch.setattr(adapter, "_installer", installer)
    result = adapter.execute(
        tmp_path, tmp_path / "out", tmp_path / "temp", tmp_path / "capsule", operation="poetry.describe"
    )
    assert result["requirements"] == ["idna==3.10"]
    assert result["lock_preserved"] is True
    assert result["production_eligible"] is False
    assert calls == [(["main", "testing"], ["native"])]
    assert (tmp_path / "poetry.lock").read_text() == "unchanged lock fixture"
    assert not (tmp_path / "out").exists()


def test_root_install_uses_upstream_editable_builder_after_dependency_install(tmp_path, monkeypatch):
    import sys
    from types import ModuleType

    observed = []
    io_module = ModuleType("cleo.io.null_io")
    io_module.NullIO = lambda: object()
    builder_module = ModuleType("poetry.masonry.builders.editable")

    class Builder:
        def __init__(self, poetry, environment, io):
            observed.append((poetry, environment))

        def build(self):
            observed.append("built")

    builder_module.EditableBuilder = Builder
    monkeypatch.setitem(sys.modules, "cleo.io.null_io", io_module)
    monkeypatch.setitem(sys.modules, "poetry.masonry.builders.editable", builder_module)
    poetry, environment = object(), object()
    adapter.install_root(poetry, environment)
    assert observed == [(poetry, environment), "built"]


def test_install_harvests_only_private_site(tmp_path, monkeypatch):
    import sys
    from types import ModuleType

    request(tmp_path)
    (tmp_path / "poetry.lock").write_text("unchanged")
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    output = tmp_path / "output"
    output.mkdir()
    poetry = SimpleNamespace(
        locker=SimpleNamespace(is_locked=lambda: True, is_fresh=lambda: True),
        package=SimpleNamespace(dependency_group_names=lambda **kw: {"main"}, extras={}),
        is_package_mode=False,
    )
    monkeypatch.setattr(adapter, "_project", lambda *args: poetry)
    module = ModuleType("poetry.utils.env")
    module.SystemEnv = lambda path: object()
    calls = []

    def build_venv(prefix, *, executable, with_pip):
        calls.append((prefix, executable, with_pip))
        (prefix / "lib/site-packages").mkdir(parents=True)
        (prefix / "bin").mkdir()
        (prefix / "bin/customer-script").write_text("private launcher")

    def environment(prefix):
        paths = {
            "purelib": str(prefix / "lib/site-packages"),
            "platlib": str(prefix / "lib/site-packages"),
            "scripts": str(prefix / "bin"),
            "data": str(prefix),
            "include": str(prefix / "include"),
        }
        return SimpleNamespace(paths=paths, scheme_dict=paths)

    module.EnvManager = SimpleNamespace(build_venv=build_venv)
    module.VirtualEnv = environment
    monkeypatch.setitem(sys.modules, "poetry.utils.env", module)
    sentinel = object()
    monkeypatch.setattr(adapter, "_offline_executor", lambda *args: sentinel)

    def installer(poetry, env, groups, extras, executor):
        def run():
            if executor is sentinel:
                (temporary / "poetry-env/lib/site-packages/customer.py").write_text("fixture")
                return 0
            return executor.execute([])

        return SimpleNamespace(run=run)

    monkeypatch.setattr(adapter, "_installer", installer)
    result = adapter.execute(tmp_path, output, temporary, tmp_path / "capsule", operation="poetry.install")
    assert result["status"] == "COMPLETE"
    assert calls == [(temporary / "poetry-env", Path(sys.executable), False)]
    assert (output / "site-packages/customer.py").read_text() == "fixture"
    assert sorted(path.name for path in output.iterdir()) == ["site-packages"]
    assert (tmp_path / "poetry.lock").read_text() == "unchanged"


def test_wheelhouse_directory_cannot_be_an_alias(tmp_path):
    root = tmp_path / "real"
    root.mkdir()
    wheel = root / "idna-3.10-py3-none-any.whl"
    wheel.write_bytes(b"fixture")
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    package = SimpleNamespace(
        files=[{"file": wheel.name, "hash": "sha256:" + hashlib.sha256(wheel.read_bytes()).hexdigest()}]
    )
    with pytest.raises(ProjectRuntimeError, match="wheelhouse_invalid"):
        adapter.local_wheel(alias, wheel.name, package)


def test_selected_git_operations_become_exact_source_declarations():
    package = SimpleNamespace(
        name="poetry-core",
        version="2.5.0.dev0",
        source_type="git",
        source_url="https://github.com/python-poetry/poetry-core.git",
        source_reference="HEAD",
        source_resolved_reference="b9663e42c808543377ae523611c4cfad68016f30",
        source_subdirectory=None,
    )
    operation = SimpleNamespace(package=package, skipped=False, job_type="install")
    assert adapter.acquisition_requirements([operation]) == []
    declaration = adapter.acquisition_sources([operation])[0]
    assert declaration["commit"] == package.source_resolved_reference
    assert declaration["url"] == package.source_url
    package.source_resolved_reference = None
    with pytest.raises(ProjectRuntimeError, match="source_request_invalid"):
        adapter.acquisition_sources([operation])


def resolution_request():
    return {
        "schema": "native-poetry-resolution-v1",
        "pyproject": {
            "project": {
                "name": "ordinary",
                "version": "1",
                "requires-python": ">=3.11,<3.12",
                "dependencies": ["idna>=3.10,<4"],
            },
            "tool": {"poetry": {"package-mode": False}},
        },
        "content_hash": "a" * 64,
        "groups": ["main"],
        "extras": [],
    }


def test_missing_lock_describes_metadata_without_running_installer(tmp_path, monkeypatch):
    request(tmp_path)
    poetry = SimpleNamespace(
        package=SimpleNamespace(dependency_group_names=lambda **kw: {"main"}, extras={}), is_package_mode=False
    )
    monkeypatch.setattr(adapter, "_project", lambda *args: poetry)
    monkeypatch.setattr(adapter, "resolution_request", lambda *args: resolution_request())
    monkeypatch.setattr(adapter, "_installer", lambda *args: pytest.fail("resolution must not run in hook worker"))
    result = adapter.execute(
        tmp_path, tmp_path / "out", tmp_path / "temporary", tmp_path / "capsule", operation="poetry.describe"
    )
    assert result["locked"] is False
    assert result["resolution"] == resolution_request()
    assert not (tmp_path / "poetry.lock").exists()


@pytest.mark.parametrize(
    "alter",
    [
        lambda v: v.update(host=True),
        lambda v: v["pyproject"].update(**{"build-system": {"build-backend": "unsafe"}}),
        lambda v: v["pyproject"]["project"].update(dependencies=["dep @ https://example.org/source.tar.gz"]),
        lambda v: v["pyproject"]["tool"]["poetry"].update(
            dependencies={"dep": {"git": "https://example.org/repo.git"}}
        ),
        lambda v: v.update(content_hash="bad"),
    ],
)
def test_resolution_request_rejects_nonmetadata_inputs(alter):
    value = resolution_request()
    alter(value)
    with pytest.raises(ProjectRuntimeError, match=r"resolution_.*invalid|source_unsupported"):
        adapter.validate_resolution_request(value)


def test_resolution_request_preserves_complete_group_and_extra_declarations():
    value = resolution_request()
    value["pyproject"]["project"]["optional-dependencies"] = {"native": ["charset-normalizer>=3"]}
    value["pyproject"]["dependency-groups"] = {
        "testing": ["pytest>=8", {"include-group": "common"}],
        "common": ["idna>=3"],
    }
    value["pyproject"]["tool"]["poetry"]["group"] = {"docs": {"optional": True, "dependencies": {"sphinx": "^8"}}}
    assert adapter.validate_resolution_request(value) == value


def test_resolution_metadata_strips_project_hooks_and_config():
    data = resolution_request()["pyproject"]
    data["project"].update(readme="README.md", scripts={"unsafe": "hook:main"})
    data["build-system"] = {"build-backend": "hook", "backend-path": ["."]}
    data["tool"]["poetry"].update(packages=[{"include": "unsafe"}], scripts={"unsafe": "hook:main"})
    package = SimpleNamespace(all_requires=[SimpleNamespace(source_type=None, source_name=None)])
    poetry = SimpleNamespace(
        pyproject=SimpleNamespace(data=data),
        package=package,
        locker=SimpleNamespace(_get_content_hash=lambda: "a" * 64),
    )
    assert adapter.resolution_request(poetry, ["main"], []) == resolution_request()


def test_resolution_direct_origin_is_denied_before_any_manager_source_search():
    with pytest.raises(ProjectRuntimeError, match="resolution_source_unsupported"):
        adapter.deny_resolution_source(object(), object())


def test_resolution_sdist_metadata_is_denied_before_any_build():
    with pytest.raises(ProjectRuntimeError, match="resolution_metadata_unavailable"):
        adapter.deny_sdist_metadata(object(), object())
