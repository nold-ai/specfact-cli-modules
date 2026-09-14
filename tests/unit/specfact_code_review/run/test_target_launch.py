"""Target namespaces cannot write their supervisor results."""

import json

import pytest

from specfact_code_review.run import target_launch
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
    assert environment(target_command("python-argv", []))["SPECFACT_TARGET_PYTEST"] == "1"
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
