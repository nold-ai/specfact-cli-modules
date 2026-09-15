"""Target namespaces cannot write their supervisor results."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from specfact_code_review.run import target_bootstrap, target_launch
from specfact_code_review.run.target_launch import target_command


@pytest.fixture(autouse=True)
def empty_member_domains(tmp_path, monkeypatch):

    (tmp_path / "project-runtime.json").write_text(
        json.dumps(
            {
                "inventory": {
                    "member_graphs": {
                        name: {"sealed_imports": [], "installed": []} for name in ("pylint", "pytest-observe")
                    }
                }
            }
        )
    )
    sealed = tmp_path / "sealed-empty"
    sealed.mkdir()
    monkeypatch.setattr(target_launch, "PROJECT", tmp_path)
    monkeypatch.setattr(target_launch, "SEALED", sealed)


def test_target_worker_cannot_write_controller_output_or_share_pid_namespace() -> None:

    argv = target_command("pylint", ["app.py"])
    assert "--unshare-all" in argv
    assert "--share-net" not in argv
    assert argv[argv.index("--ro-bind") + 1 : argv.index("--ro-bind") + 3] == ["/", "/"]
    assert argv[argv.index("/opt/specfact/output") - 1 : argv.index("/opt/specfact/output") + 1] == [
        "--tmpfs",
        "/opt/specfact/output",
    ]
    assert "/opt/specfact/builtin/specfact_code_review/run/target_bootstrap.py" in argv


def test_project_python_preserves_extensionless_script_arguments(monkeypatch) -> None:

    captured = []
    monkeypatch.setattr(target_launch.sys, "argv", ["python", "manage", "--version"])
    monkeypatch.setattr(target_launch.os, "execv", lambda executable, argv: captured.append(argv))
    target_launch.main()
    assert captured[0][-3:] == ["python-argv", "manage", "--version"]


def test_native_worker_uses_matching_loader_without_mutating_supervisor(tmp_path, monkeypatch) -> None:

    loader = tmp_path / "native/ld-linux-x86-64.so.2"
    loader.parent.mkdir()
    loader.touch()
    monkeypatch.setattr(target_launch, "PROJECT", tmp_path)
    command = target_launch.interpreter_command(["-I", "-S", "worker.py"])
    assert command == [
        str(loader),
        "--library-path",
        str(loader.parent),
        "/opt/specfact/python/bin/python",
        "-I",
        "-S",
        "worker.py",
    ]
    target = target_launch.target_command("pytest-observe", ["{}"])
    assert "--setenv" not in target[target.index("--library-path") :]
    assert "LD_LIBRARY_PATH" not in target


def test_offline_target_has_private_localhost_resolution() -> None:

    command = target_command("pytest-observe", [])
    assert "/opt/specfact/project-runtime/worker-config" in command
    assert "/etc" in command
    assert "--unshare-all" in command
    assert "--share-net" not in command


def test_pytest_children_keep_private_coverage_and_their_member_domain(monkeypatch) -> None:

    def environment(command):
        return {command[index + 1]: command[index + 2] for index, arg in enumerate(command) if arg == "--setenv"}

    parent = environment(target_command("pytest-observe", []))
    assert parent["COVERAGE_FILE"] == "/opt/specfact/tmp/.coverage"
    assert parent["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert parent["SPECFACT_TARGET_PYTEST"] == "1"
    monkeypatch.setenv("SPECFACT_TARGET_PYTEST", "1")
    assert environment(target_command("python-argv", []))["SPECFACT_TARGET_PYTEST"] == "0"
    assert environment(target_command("pylint", []))["SPECFACT_TARGET_PYTEST"] == "0"


def test_member_mounts_expose_only_recorded_distribution_files(tmp_path, monkeypatch) -> None:

    sealed = tmp_path / "sealed"
    sealed.mkdir()
    for name in ("pylint", "pylint-4.0.7.dist-info", "unrelated", "unrelated-1.0.dist-info"):
        (sealed / name).mkdir()
    (tmp_path / "project-runtime.json").write_text(
        json.dumps(
            {
                "inventory": {
                    "member_graphs": {
                        "pylint": {
                            "sealed_imports": ["pylint"],
                            "installed": [{"name": "pylint", "origin": "analyzer"}],
                        }
                    }
                }
            }
        )
    )
    monkeypatch.setattr(target_launch, "PROJECT", tmp_path)
    monkeypatch.setattr(target_launch, "SEALED", sealed)
    mounts = target_launch.member_mounts("pylint")
    assert str(sealed / "pylint") in mounts
    assert str(sealed / "pylint-4.0.7.dist-info") in mounts
    assert str(sealed / "unrelated") not in mounts
    assert str(sealed / "unrelated-1.0.dist-info") not in mounts


def _nested_child_policy(tmp_path, monkeypatch, location, remove_home):
    """Execute a real child using the emitted launch policy; no Linux bwrap emulation claim."""

    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    cwd = tmp_path / location
    cwd.mkdir(parents=True, exist_ok=True)
    (cwd / "data.txt").write_text("parent-data")
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("CUSTOMER_CONFIG", "caller-overlay")
    monkeypatch.setenv("HOME", "caller-home")
    if remove_home:
        monkeypatch.delenv("HOME")
    probe = (
        "import os,json; from pathlib import Path; "
        "print(json.dumps([os.getenv('CUSTOMER_CONFIG'),os.getenv('HOME'),os.getcwd(),"
        "Path('data.txt').read_text() if Path('data.txt').exists() else None]))"
    )
    observed = []

    def execute(_executable, command):
        environment = dict(os.environ)
        directory = cwd
        if "--clearenv" in command:
            environment = {command[i + 1]: command[i + 2] for i, arg in enumerate(command) if arg == "--setenv"}
            directory = snapshot
        child = subprocess.run(
            [sys.executable, "-c", probe], cwd=directory, env=environment, capture_output=True, text=True, check=True
        )
        observed.append(json.loads(child.stdout))

    monkeypatch.setattr(target_launch.sys, "argv", ["python", "-c", probe])
    monkeypatch.setattr(target_launch.os, "execv", execute)
    target_launch.main()
    return observed[0], str(cwd)


@pytest.mark.parametrize("location", ["snapshot/subdirectory", "private-tmp/case"])
@pytest.mark.parametrize("remove_home", [False, True])
def test_nested_python_preserves_caller_environment_cwd_and_files(tmp_path, monkeypatch, location, remove_home):
    observed, cwd = _nested_child_policy(tmp_path, monkeypatch, location, remove_home)
    assert observed == ["caller-overlay", None if remove_home else "caller-home", cwd, "parent-data"]


def test_first_entry_never_inherits_context_from_environment(monkeypatch):
    monkeypatch.setenv("SPECFACT_PROJECT_PYTHON", "1")
    monkeypatch.setenv("SPECFACT_TARGET_PYTEST", "1")
    monkeypatch.setenv("CUSTOMER_CONFIG", "must-not-leak")
    command = target_command("pylint", [])
    assert "--clearenv" in command and "--unshare-all" in command
    assert "CUSTOMER_CONFIG" not in command
    assert command[command.index("--chdir") + 1] == "/opt/specfact/snapshot"


@pytest.mark.parametrize(
    "domain,relative",
    [
        ("project-python", "run/target_bootstrap.py"),
        ("pytest-observe", "run/target_pytest.py"),
        ("pylint", "run/target_pylint.py"),
        ("basedpyright", "tools/basedpyright_runner.py"),
        ("crosshair", "tools/contract_runner.py"),
    ],
)
def test_nested_member_domain_survives_environment_replacement(tmp_path, monkeypatch, domain, relative):

    builtin = Path(target_launch.__file__).parents[2]
    context = tmp_path / "context"
    context.symlink_to(builtin / "specfact_code_review" / relative)
    monkeypatch.setattr(target_launch, "CONTEXT", context, raising=False)
    monkeypatch.setattr(target_launch, "BUILTIN", builtin, raising=False)
    monkeypatch.delenv("SPECFACT_TARGET_PYTEST", raising=False)
    assert target_launch.execution_domain() == domain
    monkeypatch.setenv("SPECFACT_TARGET_PYTEST", "forged-role")
    assert target_launch.execution_domain() == domain


def test_unrecognized_namespace_context_is_rejected(tmp_path, monkeypatch):
    context = tmp_path / "context"
    context.write_text("pytest-observe")
    monkeypatch.setattr(target_launch, "CONTEXT", context, raising=False)
    with pytest.raises(RuntimeError, match="project_python_context"):
        target_launch.execution_domain()


def _native_nested_wrapper(tmp_path, domain):
    """Relocate absolute capsule paths only; execute the actual launcher and bootstrap."""

    builtin, project = tmp_path / "builtin", tmp_path / "runtime"
    context, member = tmp_path / "context", tmp_path / "member"
    member.mkdir()
    (member / "analyzer_only.py").write_text('VALUE = "member-owned"\n')
    installed = project / "site-packages"
    installed.mkdir(parents=True)
    (installed / "customer_dependency.py").write_text('VALUE = "project-owned"\n')
    descriptor = {
        "project": {"source_roots": []},
        "inventory": {"member_graphs": {domain: {"sealed_imports": ["analyzer_only"], "installed": []}}},
    }
    (project / "project-runtime.json").write_text(json.dumps(descriptor))
    replacements = {
        "/opt/specfact/project-runtime": str(project),
        "/opt/specfact/builtin": str(builtin),
        "/opt/specfact/config/python-context": str(context),
        "/opt/specfact/config/member-analyzers": str(member),
        "/opt/specfact/python/bin/python": sys.executable,
    }
    source_root = Path(target_bootstrap.__file__).parents[2]
    files = {
        *target_launch.DOMAIN_FILES.values(),
        "specfact_code_review/run/target_launch.py",
        "specfact_code_review/run/sitecustomize.py",
    }
    for relative in files:
        content = (source_root / relative).read_text()
        for original, replacement in replacements.items():
            content = content.replace(original, replacement)
        destination = builtin / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
    context.symlink_to(builtin / target_launch.DOMAIN_FILES[domain])
    wrapper = project / "bin/python"
    wrapper.parent.mkdir()
    wrapper.write_text(
        f"#!{sys.executable}\nimport runpy\n"
        f"runpy.run_path({str(builtin / 'specfact_code_review/run/target_launch.py')!r}, run_name='__main__')\n"
    )
    wrapper.chmod(0o700)
    return wrapper


@pytest.mark.parametrize("domain", ["project-python", "pytest-observe", "pylint", "basedpyright", "crosshair"])
@pytest.mark.parametrize("environment", [{}, {"CUSTOMER_CONFIG": "caller-overlay", "HOME": "caller-home"}])
def test_actual_nested_exec_preserves_environment_and_member_imports(tmp_path, domain, environment):

    wrapper = _native_nested_wrapper(tmp_path, domain)
    cwd = tmp_path / "private-tmp/case"
    cwd.mkdir(parents=True)
    (cwd / "data.txt").write_text("parent-data")
    probe = (
        "import os,json,customer_dependency; from pathlib import Path; "
        "print(json.dumps([os.getenv('HOME'),os.getcwd(),Path('data.txt').read_text(),"
        "customer_dependency.VALUE,os.getenv('CUSTOMER_CONFIG')]))"
    )
    if domain != "project-python":
        probe += "; import analyzer_only; assert analyzer_only.VALUE == 'member-owned'"
    completed = subprocess.run(
        [str(wrapper), "-c", probe], env=environment, cwd=cwd, capture_output=True, text=True, timeout=30, check=False
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == [
        environment.get("HOME"),
        str(cwd),
        "parent-data",
        "project-owned",
        environment.get("CUSTOMER_CONFIG"),
    ]
