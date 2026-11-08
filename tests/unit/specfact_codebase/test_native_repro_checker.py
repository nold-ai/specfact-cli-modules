import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import certifi
import pytest
import yaml
from specfact_cli.utils import env_manager
from specfact_cli.utils.env_manager import EnvManager, EnvManagerInfo

from specfact_codebase.validators.repro_checker import CheckStatus, ReproChecker


@pytest.fixture
def repro_repo(tmp_path: Path) -> Path:
    config = tmp_path / "tools/semgrep/async.yml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "rules:\n  - id: command-injection-risk\n    languages: [python]\n"
        "    pattern: subprocess.run(..., shell=True, ...)\n    message: unsafe shell\n    severity: WARNING\n",
        encoding="utf-8",
    )
    (tmp_path / "example.py").write_text(
        "import subprocess\n\ndef check(cmd):\n    enabled = True\n    disabled = False\n"
        "    subprocess.run(cmd, shell=True)\n    subprocess.run(cmd, shell=enabled)\n"
        "    subprocess.run(cmd, shell=False)\n    subprocess.run(cmd, shell=disabled)\n",
        encoding="utf-8",
    )
    return tmp_path


def _select_scanner(monkeypatch: pytest.MonkeyPatch, environment: EnvManagerInfo) -> None:
    probe = env_manager.check_tool_in_env
    monkeypatch.setattr(env_manager, "detect_env_manager", lambda _root: environment)
    monkeypatch.setattr(
        env_manager,
        "check_tool_in_env",
        lambda root, tool, info: (
            probe(root, tool, info)
            if tool in {"semgrep", "osemgrep"}
            else (False, "Tool excluded from this scanner test")
        ),
    )


def test_codebase_repro_runs_native_scanner_without_python_cli(
    repro_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = shutil.which("osemgrep")
    if executable is None:
        pytest.skip("upstream native Semgrep executable is required")
    monkeypatch.setenv("PATH", str(Path(executable).parent) + os.pathsep + os.defpath)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    assert shutil.which("semgrep") is None
    environment = EnvManagerInfo(manager=EnvManager.UNKNOWN, available=False, command_prefix=[])
    _select_scanner(monkeypatch, environment)
    report = ReproChecker(repo_path=repro_repo).run_all_checks()
    result = next(check for check in report.checks if check.tool == "semgrep")
    assert result.status is CheckStatus.PASSED, result.error
    assert "command-injection-risk" in result.output
    lines = {int(match) for match in re.findall(r"(?m)^\s*(\d+)\s*┆", result.output)}
    assert lines == {6, 7}


@pytest.mark.parametrize("python_only", [False, True])
def test_codebase_repro_missing_native_reports_truthful_guidance(
    repro_repo: Path, monkeypatch: pytest.MonkeyPatch, python_only: bool
) -> None:
    environment = EnvManagerInfo(manager=EnvManager.UNKNOWN, available=False, command_prefix=[])
    monkeypatch.setattr(shutil, "which", lambda tool: "/tools/semgrep" if python_only and tool == "semgrep" else None)
    monkeypatch.setattr(subprocess, "run", lambda command, **_kwargs: subprocess.CompletedProcess(command, 0))
    _select_scanner(monkeypatch, environment)
    report = ReproChecker(repo_path=repro_repo).run_all_checks()
    result = next(check for check in report.checks if check.tool == "semgrep")
    assert result.status is CheckStatus.SKIPPED
    assert "osemgrep" in result.error
    assert "pip install" not in result.error


@pytest.mark.parametrize("fix", [False, True])
@pytest.mark.parametrize("override", [False, True])
@pytest.mark.parametrize("library", [None, "", "/caller/libraries"])
def test_codebase_repro_preserves_managed_command_timeout_and_ca(
    repro_repo: Path, monkeypatch: pytest.MonkeyPatch, fix: bool, override: bool, library: str | None
) -> None:
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    if library is not None:
        monkeypatch.setenv("LD_LIBRARY_PATH", library)
    environment = EnvManagerInfo(manager=EnvManager.UV, available=True, command_prefix=["uv", "run"])
    monkeypatch.setattr(env_manager, "detect_env_manager", lambda _root: environment)
    monkeypatch.setattr(
        env_manager, "check_tool_in_env", lambda _root, tool, _info: (tool in {"semgrep", "osemgrep"}, None)
    )
    monkeypatch.setattr(shutil, "which", lambda _tool: "/tools/uv")
    if override:
        monkeypatch.setenv("SSL_CERT_FILE", "/explicit/owner-ca.pem")
    else:
        monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    observed: list[tuple[list[str], dict[str, object]]] = []
    original_run = subprocess.run
    monkeypatch.setattr(subprocess, "_text_encoding", lambda: "cp1252")

    def scan(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        observed.append((command, kwargs.copy()))
        stdout, stderr = "scan result ←".encode(), "native ← stderr".encode()
        program = f"import os;os.write(1,{stdout!r});os.write(2,{stderr!r})"
        return original_run([sys.executable, "-I", "-S", "-c", program], check=kwargs.pop("check", False), **kwargs)

    monkeypatch.setattr(subprocess, "run", scan)
    report = ReproChecker(repo_path=repro_repo, budget=120, fix=fix).run_all_checks()
    result = next(check for check in report.checks if check.tool == "semgrep")
    assert (result.status, result.output, result.error) == (CheckStatus.PASSED, "scan result ←", "native ← stderr")
    assert len(observed) == 1
    command, options = observed[0]
    assert command == [
        "uv",
        "run",
        "osemgrep",
        "scan",
        "--experimental",
        "--metrics=off",
        "--disable-version-check",
        "--config",
        "tools/semgrep/async.yml",
        ".",
        *(["--autofix"] if fix else []),
    ]
    assert options["timeout"] == 30
    assert options["cwd"] == repro_repo
    environment_vars = options["env"]
    assert isinstance(environment_vars, dict)
    assert environment_vars["SSL_CERT_FILE"] == ("/explicit/owner-ca.pem" if override else certifi.where())
    assert environment_vars["SEMGREP_LOG_FILE"] == str(repro_repo / ".specfact/logs/semgrep.log")
    actual = environment_vars.get("LD_LIBRARY_PATH")
    assert actual == ("$ORIGIN/libs" if library is None else library)


def test_codebase_manifest_declares_direct_certifi() -> None:
    root = Path(__file__).resolve().parents[3]
    manifest = yaml.safe_load((root / "packages/specfact-codebase/module-package.yaml").read_text(encoding="utf-8"))
    assert "certifi" in manifest["pip_dependencies"]
