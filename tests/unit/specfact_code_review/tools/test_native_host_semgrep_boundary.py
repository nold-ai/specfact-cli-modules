from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import certifi
import pytest

from specfact_code_review import _review_utils
from specfact_code_review.run import native_worker
from specfact_code_review.tools import semgrep_runner, tool_availability


@pytest.mark.parametrize(("native_present", "python_present"), [(False, True), (True, False), (True, True)])
def test_host_discovery_requires_native_semgrep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native_present: bool, python_present: bool
) -> None:
    commands = {}
    if python_present:
        commands["semgrep"] = "/python/semgrep"
    if native_present:
        commands["osemgrep"] = "/native/osemgrep"
    monkeypatch.setattr(tool_availability.shutil, "which", commands.get)

    findings = tool_availability.skip_if_tool_missing("semgrep", tmp_path / "source.py")

    assert bool(findings) is not native_present
    if findings:
        assert "osemgrep" in findings[0].message
        assert "pip install" not in findings[0].message


@pytest.mark.parametrize("platform", ["linux", "darwin"])
@pytest.mark.parametrize("override", [None, "", "/caller/value"])
def test_host_native_command_preserves_unicode_and_explicit_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, override: str | None
) -> None:
    monkeypatch.setattr(sys, "platform", platform)
    for name in ("SSL_CERT_FILE", "LD_LIBRARY_PATH"):
        monkeypatch.delenv(name, raising=False)
        if override is not None:
            monkeypatch.setenv(name, override)
    original_run = subprocess.run
    monkeypatch.setattr(subprocess, "_text_encoding", lambda: "cp1252")
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs.copy()))
        return original_run(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                "import os;os.write(1,'雪 ← café'.encode());os.write(2,'← stderr'.encode())",
            ],
            **kwargs,
        )

    monkeypatch.setattr(semgrep_runner.subprocess, "run", run)
    source = tmp_path / "source with spaces.py"
    configs = [tmp_path / "first rules.yml", tmp_path / "second.yml"]

    result = semgrep_runner._run_semgrep_command([source], bundle_root=None, config_file=configs)

    assert (result.stdout, result.stderr) == ("雪 ← café", "← stderr")
    command, options = calls[0]
    assert command == [
        "osemgrep",
        "scan",
        "--experimental",
        "--metrics=off",
        "--disable-version-check",
        "--quiet",
        "--disable-nosem",
        "--config",
        str(configs[0]),
        "--config",
        str(configs[1]),
        "--json",
        str(source),
    ]
    assert options["timeout"] == semgrep_runner.SEMGREP_TIMEOUT_SECONDS
    assert options["env"]["SSL_CERT_FILE"] == (certifi.where() if override is None else override)
    expected_library = "$ORIGIN/libs" if platform == "linux" else None
    assert options["env"].get("LD_LIBRARY_PATH") == (expected_library if override is None else override)


def test_native_host_rejects_malformed_utf8(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_run = subprocess.run
    monkeypatch.setattr(subprocess, "_text_encoding", lambda: "cp1252")

    def run(_command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return original_run([sys.executable, "-I", "-S", "-c", "import os;os.write(1,b'\\xff')"], **kwargs)

    monkeypatch.setattr(semgrep_runner.subprocess, "run", run)

    with pytest.raises(UnicodeDecodeError):
        semgrep_runner._run_semgrep_command(
            [tmp_path / "source.py"], bundle_root=None, config_file=tmp_path / "rules.yml"
        )


def test_sealed_semgrep_discovery_does_not_accept_python_alone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_review_utils, "__file__", "/opt/specfact/builtin/specfact_code_review/_review_utils.py")
    monkeypatch.setattr(
        tool_availability.shutil, "which", lambda name: "/python/bin/python" if "python" in name else None
    )

    assert tool_availability.skip_if_tool_missing("semgrep", tmp_path / "source.py")


@pytest.mark.parametrize(
    ("member", "config_name"), [("semgrep-clean", "clean_code.yaml"), ("semgrep-bugs", "bugs.yaml")]
)
def test_actual_native_semgrep_adapter_preserves_closed_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, member: str, config_name: str
) -> None:
    for name in (*native_worker._UNSAFE_ENVIRONMENT, "SSL_CERT_FILE", "LD_LIBRARY_PATH", "SEMGREP_SEND_METRICS"):
        monkeypatch.delenv(name, raising=False)
    capsule, project, temporary = (tmp_path / name for name in ("capsule", "project", "temporary"))
    for root in (capsule, project, temporary):
        root.mkdir()
    rules = project / ".specfact-native-config" / "rules"
    (rules / ".semgrep").mkdir(parents=True)
    (rules / ".semgrep" / config_name).write_text("rules: []\n", encoding="utf-8")
    source = project / "source.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    transport = native_worker.ReplayTransport(
        member=member, tool="semgrep", replies=[], capsule=capsule, project=project, temporary=temporary
    )

    with pytest.raises(native_worker.RequestPending) as pending:
        native_worker._semgrep_external_adapter(member, [source], transport.run, [str(rules)], False, False)

    request = pending.value.request
    assert request["argv"] == [
        "capsule-tool:semgrep",
        "--disable-version-check",
        "--quiet",
        "--disable-nosem",
        "--config",
        f"project/.specfact-native-config/rules/.semgrep/{config_name}",
        "--json",
        "project/source.py",
    ]
    assert request["environment"] == {
        "HOME": "temporary/semgrep-home",
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_SETTINGS_FILE": "temporary/semgrep-home/.semgrep/settings.yml",
        "XDG_CACHE_HOME": "temporary/semgrep-home/.cache",
        "XDG_CONFIG_HOME": "temporary/semgrep-home/.config",
    }
    assert request["timeout_ms"] == semgrep_runner.SEMGREP_TIMEOUT_SECONDS * 1000
    assert request["tool"] == "semgrep"
