from __future__ import annotations

import json
import os
import subprocess
import sys
from enum import IntEnum
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from specfact_code_review.run import native_tool_worker


def _roots(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    roots = (
        tmp_path / "capsule",
        tmp_path / "project",
        tmp_path / "output",
        tmp_path / "temporary",
    )
    for root in roots:
        root.mkdir(mode=0o700)
    roots[1].chmod(0o500)
    return roots


def _request(roots: tuple[Path, Path, Path, Path], tool: str, argv: list[str]) -> None:
    project = roots[1]
    project.chmod(0o700)
    path = project / native_tool_worker.REQUEST_NAME
    path.write_text(
        json.dumps(
            {
                "argv": argv,
                "capture_output": True,
                "cwd": "project",
                "environment": {},
                "member": "ruff" if tool == "ruff" else tool,
                "schema": native_tool_worker.REQUEST_SCHEMA,
                "sequence": 0,
                "text": True,
                "timeout_ms": 30_000,
                "tool": tool,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o400)
    project.chmod(0o500)


def _argv(roots: tuple[Path, Path, Path, Path], tool: str) -> list[str]:
    return ["native-tool-worker", *(str(root) for root in roots), tool]


def test_main_restores_caller_cwd_after_in_process_tool(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    _request(roots, "radon", ["capsule-tool:radon", "mi", "-j", "project/pkg/example.py"])
    caller_cwd = Path.cwd()
    caller_environment = dict(os.environ)
    caller_path = list(sys.path)
    monkeypatch.chdir(caller_cwd)
    observed: dict[str, Path] = {}

    def run_python_tool(_tool: str, _arguments: list[str], _project: Path) -> int:
        observed["cwd"] = Path.cwd()
        sys.path.append(str(roots[1]))
        return 0

    monkeypatch.setattr(native_tool_worker.sys, "argv", _argv(roots, "radon"))
    monkeypatch.setattr(native_tool_worker, "_run_python_tool", run_python_tool)
    monkeypatch.setattr(native_tool_worker, "activate_project_domain", lambda *_args: None)

    assert native_tool_worker.main() == 0
    assert observed["cwd"] == roots[1]
    assert Path.cwd() == caller_cwd
    assert dict(os.environ) == caller_environment
    assert sys.path == caller_path


def test_environment_binds_tool_state_to_private_temporary_root(tmp_path: Path) -> None:
    capsule, project, _output, temporary = _roots(tmp_path)

    environment = native_tool_worker._environment({}, capsule=capsule, project=project, temporary=temporary)

    assert environment["HOME"] == str(temporary / "home")
    assert environment["XDG_CACHE_HOME"] == str(temporary / "cache")
    assert environment["XDG_CONFIG_HOME"] == str(temporary / "config")
    assert environment["RUFF_CACHE_DIR"] == str(temporary / "ruff-cache")
    assert environment["TMPDIR"] == str(temporary / "tmp")
    for name in ("home", "cache", "config", "ruff-cache", "tmp"):
        state = temporary / name
        assert state.is_dir()
        assert state.stat().st_mode & 0o777 == 0o700


def test_ruff_plan_executes_only_fixed_capsule_image(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    caller_cwd = Path.cwd()
    monkeypatch.chdir(caller_cwd)
    target = roots[0] / "tools/ruff"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"ruff")
    target.chmod(0o500)
    source = roots[1] / "pkg/example.py"
    roots[1].chmod(0o700)
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    source.chmod(0o400)
    source.parent.chmod(0o500)
    roots[1].chmod(0o500)
    _request(roots, "ruff", ["capsule-tool:ruff", "check", "project/pkg/example.py"])
    observed: dict[str, object] = {}

    def execve(path: Path, argv: list[str], environment: dict[str, str]) -> None:
        observed.update(path=path, argv=argv, environment=environment)
        raise RuntimeError("execve intercepted")

    monkeypatch.setattr(native_tool_worker.sys, "argv", _argv(roots, "ruff"))
    monkeypatch.setattr(native_tool_worker.os, "execve", execve)

    with pytest.raises(RuntimeError, match="intercepted"):
        native_tool_worker.main()

    assert observed["path"] == target
    assert observed["argv"] == [str(target), "check", str(source)]
    environment = observed["environment"]
    assert isinstance(environment, dict)
    assert "PATH" not in environment
    assert Path.cwd() == caller_cwd


@pytest.mark.parametrize(
    ("tool", "target_suffix", "expected_prefix"),
    [
        (
            "basedpyright",
            "tools/node",
            ["--jitless", "--unhandled-rejections=warn", "--require"],
        ),
    ],
)
def test_direct_tool_plans_bind_node_and_semgrep_images(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    tool: str,
    target_suffix: str,
    expected_prefix: list[str],
) -> None:
    roots = _roots(tmp_path)
    target = roots[0] / target_suffix
    target.parent.mkdir(parents=True)
    target.write_bytes(tool.encode())
    target.chmod(0o500)
    _request(roots, tool, [f"capsule-tool:{tool}", "--version"])
    observed: dict[str, object] = {}

    def execve(path: Path, argv: list[str], _environment: dict[str, str]) -> None:
        observed.update(path=path, argv=argv)
        raise RuntimeError("execve intercepted")

    monkeypatch.setattr(native_tool_worker.sys, "argv", _argv(roots, tool))
    monkeypatch.setattr(native_tool_worker.os, "execve", execve)

    with pytest.raises(RuntimeError, match="intercepted"):
        native_tool_worker.main()

    assert observed["path"] == target
    command = observed["argv"]
    assert isinstance(command, list)
    assert command[1 : 1 + len(expected_prefix)] == expected_prefix


def test_semgrep_plan_uses_direct_single_process_core_inputs(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    roots = _roots(tmp_path)
    capsule, project, _output, temporary = roots
    target = capsule / "tools/semgrep-core"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"semgrep")
    target.chmod(0o500)
    project.chmod(0o700)
    config = project / ".specfact-native-config/1/.semgrep/clean_code.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "rules:\n  - id: sample-rule\n    languages: [python]\n    message: sample\n    severity: WARNING\n    pattern: $X == $X\n",
        encoding="utf-8",
    )
    source = project / "pkg/example.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    for path in (config, source):
        path.chmod(0o400)
    for path in (config.parent, config.parent.parent, source.parent):
        path.chmod(0o500)
    project.chmod(0o500)
    _request(
        roots,
        "semgrep",
        [
            "capsule-tool:semgrep",
            "--disable-version-check",
            "--quiet",
            "--disable-nosem",
            "--config",
            "/opt/specfact/config/1/.semgrep/clean_code.yaml",
            "--json",
            "/opt/specfact/snapshot/pkg/example.py",
        ],
    )
    observed: dict[str, object] = {}

    ca_bundle = (
        capsule / f"python/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/certifi/cacert.pem"
    )
    ca_bundle.parent.mkdir(parents=True, exist_ok=True)
    ca_bundle.write_text("test CA bundle\n", encoding="utf-8")
    ca_bundle.chmod(0o400)

    def execve(path: Path, argv: list[str], environment: dict[str, str]) -> None:
        observed.update(path=path, argv=argv, environment=environment)
        raise RuntimeError("execve intercepted")

    monkeypatch.setattr(native_tool_worker.sys, "argv", _argv(roots, "semgrep"))
    monkeypatch.setattr(native_tool_worker.os, "execve", execve)

    with pytest.raises(RuntimeError, match="intercepted"):
        native_tool_worker.main()

    assert observed["path"] == target
    command = observed["argv"]
    assert isinstance(command, list)
    assert command[:4] == [str(target), "-json_nodots", "-j", "1"]
    assert "osemgrep" not in command
    environment = observed["environment"]
    assert isinstance(environment, dict)
    assert environment["SSL_CERT_FILE"] == str(ca_bundle)
    assert "PATH" not in environment
    rules_path = Path(command[command.index("-rules") + 1])
    targets_path = Path(command[command.index("-targets") + 1])
    assert json.loads(rules_path.read_text(encoding="utf-8"))["rules"][0]["id"] == "sample-rule"
    assert json.loads(targets_path.read_text(encoding="utf-8")) == [
        "Targets",
        [
            [
                "CodeTarget",
                {
                    "analyzer": "python",
                    "path": {"fpath": str(source), "ppath": "/pkg/example.py"},
                    "products": ["sast"],
                },
            ]
        ],
    ]
    assert temporary in rules_path.parents
    assert temporary in targets_path.parents


def test_semgrep_plan_accepts_immutable_verified_capsule_rules(tmp_path: Path) -> None:
    capsule, project, _output, temporary = _roots(tmp_path)
    target = capsule / "tools/semgrep-core"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"semgrep")
    target.chmod(0o500)
    config = capsule / "python/lib/python3.12/site-packages/specfact_code_review/.semgrep/clean_code.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "rules:\n  - id: capsule-rule\n    languages: [python]\n    message: sample\n"
        "    severity: WARNING\n    pattern: $X == $X\n",
        encoding="utf-8",
    )
    source = project / "pkg/example.py"
    project.chmod(0o700)
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    for path in (config, source):
        path.chmod(0o400)
    for path in (config.parent, source.parent):
        path.chmod(0o500)
    project.chmod(0o500)

    command = native_tool_worker._semgrep_core_command(
        [
            "capsule-tool:semgrep",
            "--disable-version-check",
            "--quiet",
            "--disable-nosem",
            "--config",
            str(config),
            "--json",
            str(source),
        ],
        context=native_tool_worker._ToolCommandContext(capsule, project, temporary, 0),
        target=target,
    )

    rules_path = Path(command[command.index("-rules") + 1])
    assert json.loads(rules_path.read_text(encoding="utf-8"))["rules"][0]["id"] == "capsule-rule"


@pytest.mark.parametrize(
    ("tamper", "value"),
    [
        ("tool", "pylint"),
        ("cwd", "/tmp"),
        ("environment", {"PATH": "/usr/bin"}),
        ("argv", ["capsule-tool:ruff", "/etc/passwd"]),
    ],
)
def test_tool_request_substitution_fails_closed(
    tmp_path: Path, monkeypatch: MonkeyPatch, tamper: str, value: object
) -> None:
    roots = _roots(tmp_path)
    _request(roots, "ruff", ["capsule-tool:ruff", "--version"])
    path = roots[1] / native_tool_worker.REQUEST_NAME
    roots[1].chmod(0o700)
    path.chmod(0o600)
    document = json.loads(path.read_text(encoding="utf-8"))
    document[tamper] = value
    path.write_text(json.dumps(document), encoding="utf-8")
    path.chmod(0o400)
    roots[1].chmod(0o500)
    monkeypatch.setattr(native_tool_worker.sys, "argv", _argv(roots, "ruff"))

    assert native_tool_worker.main() == 76


def test_logical_config_and_snapshot_paths_stay_in_project(
    tmp_path: Path,
) -> None:
    capsule, project, _output, temporary = _roots(tmp_path)

    assert native_tool_worker._materialize(
        "/opt/specfact/snapshot/pkg/example.py",
        capsule=capsule,
        project=project,
        temporary=temporary,
    ) == str(project / "pkg/example.py")
    assert native_tool_worker._materialize(
        "/opt/specfact/config/1/ruff.toml",
        capsule=capsule,
        project=project,
        temporary=temporary,
    ) == str(project / ".specfact-native-config/1/ruff.toml")
    with pytest.raises(native_tool_worker.ToolRequestError, match="absolute host path"):
        native_tool_worker._materialize(
            "/etc/passwd",
            capsule=capsule,
            project=project,
            temporary=temporary,
        )


def test_pytest_plan_materializes_fixed_embedded_evidence_paths(tmp_path: Path) -> None:
    capsule, project, _output, temporary = _roots(tmp_path)
    request = {
        "argv": [
            "capsule-tool:pytest",
            "--cov-report=json:temporary/pytest-evidence/coverage.json",
            "--junitxml=temporary/pytest-evidence/junit.xml",
            "cache_dir=temporary/pytest/cache-dir",
        ]
    }

    assert native_tool_worker._mapped_arguments(
        request,
        capsule=capsule,
        project=project,
        temporary=temporary,
    ) == [
        "capsule-tool:pytest",
        f"--cov-report=json:{temporary / 'pytest-evidence/coverage.json'}",
        f"--junitxml={temporary / 'pytest-evidence/junit.xml'}",
        f"cache_dir={temporary / 'pytest/cache-dir'}",
    ]


def test_python_tool_exit_code_accepts_bounded_integer_enum() -> None:
    class ToolExit(IntEnum):
        OK = 0
        USAGE = 4

    assert native_tool_worker._exit_code(ToolExit.OK) == 0
    assert native_tool_worker._exit_code(ToolExit.USAGE) == 4


def test_python_tool_activates_only_staged_project_and_dependency_roots(tmp_path: Path) -> None:
    project = tmp_path / "project"
    dependency = project / ".specfact-project-runtime/site-packages/fixture_dep/__init__.py"
    dependency.parent.mkdir(parents=True)
    dependency.write_text("VALUE = 7\n", encoding="utf-8")
    (project / "customer_pkg").mkdir()
    (project / "customer_pkg/__init__.py").write_text("VALUE = 5\n", encoding="utf-8")
    for path in project.rglob("*"):
        path.chmod(0o500 if path.is_dir() else 0o400)
    project.chmod(0o500)
    before = list(sys.path)
    try:
        native_tool_worker._activate_project_runtime(project)
        assert sys.path[-2:] == [str(project), str(dependency.parents[1])]
    finally:
        sys.path[:] = before


def test_python_tool_activates_staged_project_without_dependency_runtime(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir(mode=0o500)
    before = list(sys.path)
    try:
        native_tool_worker._activate_project_runtime(project)
        assert sys.path[-1] == str(project)
    finally:
        sys.path[:] = before


def test_python_tool_uses_bound_source_roots_before_installed_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    runtime = project / ".specfact-project-runtime"
    (runtime / "site-packages").mkdir(parents=True)
    source = project / "src"
    source.mkdir()
    (runtime / "project-runtime.json").write_text(json.dumps({"inventory": {"source_roots": ["src"]}}))
    for path in project.rglob("*"):
        path.chmod(0o500 if path.is_dir() else 0o400)
    project.chmod(0o500)
    before = list(sys.path)
    try:
        native_tool_worker._activate_project_runtime(project)
        assert sys.path.index(str(source)) < sys.path.index(str(runtime / "site-packages"))
        assert sys.path[: len(before)] == before
    finally:
        sys.path[:] = before


def test_native_domain_uses_project_dependency_and_denies_unrelated_analyzer_fallback(tmp_path: Path) -> None:
    capsule, project, _output, _temporary = _roots(tmp_path)
    sealed = capsule / f"python/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    sealed.mkdir(parents=True)
    (sealed / "owned_tool.py").write_text("VALUE='sealed-tool'\n")
    (sealed / "shared.py").write_text("VALUE='wrong-sealed-version'\n")
    (sealed / "unrelated.py").write_text("VALUE='must-not-fallback'\n")
    info = sealed / "owned_tool-1.dist-info"
    info.mkdir()
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: owned-tool\nVersion: 1\n")
    (info / "RECORD").write_text("owned_tool.py,,\nowned_tool-1.dist-info/METADATA,,\n")
    project.chmod(0o700)
    runtime = project / ".specfact-project-runtime"
    site = runtime / "site-packages"
    site.mkdir(parents=True)
    (site / "shared.py").write_text("VALUE='project-version'\n")
    (project / "owned_tool.py").write_text("VALUE='must-not-shadow-entry'\n")
    graph = {
        "sealed_imports": ["owned_tool"],
        "installed": [{"name": "owned-tool", "version": "1", "origin": "analyzer"}],
    }
    (runtime / "project-runtime.json").write_text(json.dumps({"inventory": {"member_graphs": {"pylint": graph}}}))
    from specfact_code_review.run.native_analyzer_view import VIEW_NAME, build_analyzer_view

    build_analyzer_view(sealed, project / VIEW_NAME, graph)
    for path in project.rglob("*"):
        path.chmod(0o500 if path.is_dir() else 0o400)
    project.chmod(0o500)
    code = (
        "import sys,json; from pathlib import Path; "
        "from specfact_code_review.run.native_tool_worker import activate_project_domain; "
        "sys.path.insert(0,sys.argv[2]); import shared,owned_tool; "
        "from specfact_code_review.run import target_bootstrap; "
        "stdlib=target_bootstrap._stdlib_paths(); "
        "target_bootstrap._stdlib_paths=lambda: [*stdlib,str(Path(sys.argv[2]).parent)]; "
        "activate_project_domain(Path(sys.argv[1]),Path(sys.argv[3]),'pylint'); "
        "assert '__main__' in sys.modules; "
        "import shared,owned_tool; "
        "assert sys.argv[2] not in sys.path; "
        "assert owned_tool.__file__.startswith(str(Path(sys.argv[1])/'.specfact-native-analyzers')); "
        "assert target_bootstrap.ImportPathFinder.find_spec('unrelated',sys.path) is None\n"
        "try: import unrelated\n"
        "except ModuleNotFoundError: denied=True\n"
        "else: denied=False\n"
        "print(json.dumps([shared.VALUE,owned_tool.VALUE,denied]))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(project), str(sealed), str(capsule)],
        env={**os.environ, "PYTHONPATH": str(Path(native_tool_worker.__file__).parents[2])},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["project-version", "sealed-tool", True]


def test_project_pytest_plugins_use_only_selected_site_entrypoints(tmp_path, monkeypatch):
    project = tmp_path / "project"
    selected = project / ".specfact-project-runtime/site-packages"
    selected.mkdir(parents=True)
    unrelated = tmp_path / "host"
    unrelated.mkdir()
    (unrelated / "host_plugin.py").write_text("raise AssertionError('host plugin loaded')")
    for root, name, entry in [
        (selected, "fixture-plugin", "fixture_plugin"),
        (unrelated, "host-plugin", "host_plugin"),
    ]:
        info = root / (name.replace("-", "_") + "-1.dist-info")
        info.mkdir()
        (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: 1\n")
        (info / "entry_points.txt").write_text(f"[pytest11]\n{name} = {entry}\n")
    (selected / "fixture_plugin.py").write_text("VALUE = 'project-plugin'\n")
    monkeypatch.syspath_prepend(str(unrelated))
    monkeypatch.syspath_prepend(str(selected))
    try:
        plugins = native_tool_worker._project_pytest_plugins(project)
        assert [plugin.VALUE for plugin, _distribution in plugins.values()] == ["project-plugin"]
        assert "host_plugin" not in sys.modules
    finally:
        sys.modules.pop("fixture_plugin", None)


def test_project_pytest_plugins_reject_ambiguous_names_before_loading(tmp_path):
    project = tmp_path / "project"
    selected = project / ".specfact-project-runtime/site-packages"
    selected.mkdir(parents=True)
    for name in ("first", "second"):
        info = selected / f"{name}-1.dist-info"
        info.mkdir()
        (info / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: 1\n")
        (info / "entry_points.txt").write_text("[pytest11]\nsame-plugin = must_not_import\n")
    with pytest.raises(native_tool_worker.ToolRequestError, match="pytest_plugin_ambiguous"):
        native_tool_worker._project_pytest_plugins(project)


def test_native_project_pytest_plugin_required_version_is_registered(tmp_path):
    from specfact_code_review.run import runner

    project = tmp_path / "project"
    site = project / ".specfact-project-runtime/site-packages"
    info = site / "fixture_plugin-1.dist-info"
    info.mkdir(parents=True)
    (info / "METADATA").write_text("Metadata-Version: 2.1\nName: fixture-plugin\nVersion: 1\n")
    (info / "entry_points.txt").write_text("[pytest11]\nfixture-plugin = fixture_plugin\n")
    (site / "fixture_plugin.py").write_text("VALUE = 1\n")
    test = project / "test_plugin.py"
    test.write_text("def test_plugin():\n    assert True\n")
    observer = project / "observer.json"
    source = str(Path(native_tool_worker.__file__).parents[2])
    arguments = [
        "capsule-tool:pytest",
        "-c",
        runner._pytest_observer_script(),
        str(observer),
        "-o",
        "required_plugins=fixture-plugin>=1",
        str(test),
    ]
    code = (
        f"import sys,os; sys.path[:0]=[{source!r}, {str(site)!r}]; "
        "os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'; "
        "from pathlib import Path; from specfact_code_review.run.native_tool_worker import _run_python_tool; "
        f"raise SystemExit(_run_python_tool('pytest', {arguments!r}, Path({str(project)!r})))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(observer.read_text())


def test_native_pytest_bounds_automatic_xdist_workers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PYTEST_XDIST_AUTO_NUM_WORKERS", "100")
    monkeypatch.setattr(native_tool_worker, "_project_pytest_plugins", lambda _project: {})
    monkeypatch.setattr(native_tool_worker.sys, "argv", list(sys.argv))
    source = "import os; assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS'] == '4'"
    assert native_tool_worker._run_python_tool("pytest", ["python", "-c", source], tmp_path) == 0
