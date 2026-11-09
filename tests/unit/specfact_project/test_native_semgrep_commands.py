from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import certifi
import pytest
import yaml
from specfact_cli.utils.env_manager import EnvManager, EnvManagerInfo

from specfact_project.analyzers.code_analyzer import CodeAnalyzer
from specfact_project.generators.test_to_openapi import OpenAPITestConverter


def test_python_only_installation_does_not_enable_native_project_scanner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: "/unexecuted/semgrep" if name == "semgrep" else None)
    monkeypatch.setattr(
        "specfact_cli.utils.env_manager.detect_env_manager",
        lambda repo_path: EnvManagerInfo(manager=EnvManager.UNKNOWN, available=False, command_prefix=[]),
    )
    analyzer = CodeAnalyzer(tmp_path)
    available, reason = analyzer._probe_semgrep()
    assert available is False
    assert reason is not None and "osemgrep" in reason
    assert "pip install" not in reason


@pytest.mark.parametrize("owner_case", [("analyzer", 0), ("analyzer", 1), ("converter", 0)])
@pytest.mark.parametrize("override", [None, "/caller/ca.pem"])
@pytest.mark.parametrize("library", [None, "", "/caller/libraries"])
def test_project_native_command_preserves_environment_timeout_and_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    owner_case: tuple[str, int],
    override: str | None,
    library: str | None,
) -> None:
    owner, returncode = owner_case
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    if library is not None:
        monkeypatch.setenv("LD_LIBRARY_PATH", library)
    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    if override is not None:
        monkeypatch.setenv("SSL_CERT_FILE", override)
    environment = EnvManagerInfo(manager=EnvManager.UV, available=True, command_prefix=["uv", "run"])
    monkeypatch.setattr("specfact_cli.utils.env_manager.detect_env_manager", lambda repo_path: environment)
    monkeypatch.setattr("specfact_cli.utils.env_manager.check_tool_in_env", lambda *args: (True, None))
    finding = {
        "check_id": "project-marker",
        "start": {"line": 6},
        "extra": {"metadata": {"kind": "feature"}, "message": "雪 ← café"},
    }
    calls: list[tuple[list[str], dict[str, Any]]] = []
    original_run = subprocess.run
    monkeypatch.setattr(subprocess, "_text_encoding", lambda: "cp1252")

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs.copy()))
        stdout = json.dumps({"results": [finding]}, ensure_ascii=False).encode()
        stderr = "native ← stderr".encode()
        program = f"import os;os.write(1,{stdout!r});os.write(2,{stderr!r});raise SystemExit({returncode})"
        result = cast(
            subprocess.CompletedProcess[str],
            original_run([sys.executable, "-I", "-S", "-c", program], check=kwargs.pop("check", False), **kwargs),
        )
        assert result.stderr == "native ← stderr"
        return result

    monkeypatch.setattr("subprocess.run", run)
    source = tmp_path / "source.py"
    source.write_text("print('example')\n", encoding="utf-8")
    config = tmp_path / "rules.yml"
    quality = tmp_path / "quality.yml"
    if owner == "analyzer":
        analyzer = object.__new__(CodeAnalyzer)
        analyzer.repo_path = tmp_path
        analyzer.semgrep_enabled = True
        analyzer.semgrep_config = config
        analyzer.semgrep_quality_config = quality
        findings = analyzer._run_semgrep_patterns(source)
        prefix = ["uv", "run"]
        timeout = 10
    else:
        converter = OpenAPITestConverter(tmp_path, semgrep_config=config)
        findings = converter._run_semgrep(source)
        prefix = []
        timeout = 5
    assert findings == [finding]
    command, kwargs = calls[-1]
    assert command[: len(prefix) + 5] == [
        *prefix,
        "osemgrep",
        "scan",
        "--experimental",
        "--metrics=off",
        "--disable-version-check",
    ]
    assert [command[index + 1] for index, value in enumerate(command) if value == "--config"] == (
        [str(config), str(quality)] if owner == "analyzer" else [str(config)]
    )
    assert kwargs["timeout"] == timeout
    assert kwargs["env"]["SSL_CERT_FILE"] == (override or certifi.where())
    assert kwargs["env"].get("LD_LIBRARY_PATH") == ("$ORIGIN/libs" if library is None else library)


def test_project_manifest_declares_direct_certificate_dependency() -> None:
    root = Path(__file__).resolve().parents[3]
    manifest = yaml.safe_load((root / "packages/specfact-project/module-package.yaml").read_text(encoding="utf-8"))
    assert "certifi" in manifest["pip_dependencies"]


@pytest.mark.parametrize(
    "output_case",
    [
        (0, '{"results": [{"check_id": "valid"}]}', "error", [{"check_id": "valid"}], None),
        (1, '{"results": [{"check_id": "valid"}]}', "warning", [{"check_id": "valid"}], None),
        (1, '{"results": [{"check_id": "valid"}]}', "ERROR", [], None),
        (1, '{"results": [{"check_id": "valid"}]}', "not found", [], None),
        (0, "not JSON", "", [], None),
        (0, "{}", "", [], None),
        (0, '{"results": null}', "", None, None),
        (0, "null", "", None, AttributeError),
        (0, "[]", "", None, AttributeError),
    ],
)
def test_analyzer_native_output_keeps_filtering_and_malformed_shape_behavior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output_case: tuple[Any, ...]
) -> None:
    returncode, stdout, stderr, expected, error = output_case
    monkeypatch.setenv("TEST_MODE", "false")
    environment = EnvManagerInfo(manager=EnvManager.UNKNOWN, available=False, command_prefix=[])
    monkeypatch.setattr("specfact_cli.utils.env_manager.detect_env_manager", lambda _root: environment)
    monkeypatch.setattr("specfact_cli.utils.env_manager.check_tool_in_env", lambda *_args: (True, None))
    monkeypatch.setattr(
        subprocess, "run", lambda *_args, **_kwargs: subprocess.CompletedProcess([], returncode, stdout, stderr)
    )
    analyzer = object.__new__(CodeAnalyzer)
    analyzer.repo_path = tmp_path
    analyzer.semgrep_enabled = True
    analyzer.semgrep_config = tmp_path / "rules.yml"
    analyzer.semgrep_quality_config = None

    if error is not None:
        with pytest.raises(error):
            analyzer._run_semgrep_patterns(tmp_path / "source.py")
    else:
        assert analyzer._run_semgrep_patterns(tmp_path / "source.py") == expected
