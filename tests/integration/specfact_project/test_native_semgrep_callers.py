from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from specfact_project.analyzers.code_analyzer import CodeAnalyzer
from specfact_project.generators.test_to_openapi import OpenAPITestConverter


@pytest.fixture
def native_analyzer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CodeAnalyzer:
    executable = shutil.which("osemgrep")
    if executable is None:
        pytest.skip("upstream native Semgrep executable is required")
    monkeypatch.setenv("PATH", str(Path(executable).parent) + os.pathsep + os.defpath)
    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    rules = tmp_path / "tools/semgrep"
    rules.mkdir(parents=True)
    (rules / "feature-detection.yml").write_text(
        "rules:\n  - id: project-shell-true\n    languages: [python]\n"
        "    pattern: subprocess.run(..., shell=True, ...)\n"
        "    message: shell execution\n    severity: WARNING\n",
        encoding="utf-8",
    )
    (rules / "code-quality.yml").write_text(
        "rules:\n  - id: project-quality-marker\n    languages: [python]\n"
        "    pattern: print(...)\n    message: marker\n    severity: INFO\n",
        encoding="utf-8",
    )
    return CodeAnalyzer(tmp_path)


@pytest.fixture
def native_source(native_analyzer: CodeAnalyzer) -> Path:
    source = native_analyzer.repo_path / "example.py"
    source.write_text(
        "import subprocess\n\ndef check(cmd):\n    enabled = True\n    disabled = False\n"
        "    subprocess.run(cmd, shell=True)\n    subprocess.run(cmd, shell=enabled)\n"
        "    subprocess.run(cmd, shell=False)\n    subprocess.run(cmd, shell=disabled)\n"
        "    print('marker')\n",
        encoding="utf-8",
    )
    return source


def test_project_native_available_without_python_cli(native_analyzer: CodeAnalyzer) -> None:
    assert shutil.which("semgrep") is None
    assert shutil.which("pysemgrep") is None
    assert native_analyzer.semgrep_enabled
    assert native_analyzer._check_semgrep_available()


def test_project_native_scan_preserves_propagation_and_both_configs(
    native_analyzer: CodeAnalyzer, native_source: Path
) -> None:
    findings = native_analyzer._run_semgrep_patterns(native_source)
    shell_lines = {
        finding["start"]["line"] for finding in findings if finding["check_id"].endswith("project-shell-true")
    }
    assert shell_lines == {6, 7}
    assert any(finding["check_id"].endswith("project-quality-marker") for finding in findings)


def test_project_converter_uses_native_scanner(native_analyzer: CodeAnalyzer, native_source: Path) -> None:
    converter = OpenAPITestConverter(native_analyzer.repo_path, semgrep_config=native_analyzer.semgrep_config)
    findings = converter._run_semgrep(native_source)
    assert {finding["start"]["line"] for finding in findings} == {6, 7}


@pytest.mark.parametrize("owner", ["analyzer", "converter"])
def test_project_native_scan_preserves_invalid_ca_override(
    native_analyzer: CodeAnalyzer, native_source: Path, monkeypatch: pytest.MonkeyPatch, owner: str
) -> None:
    certificate = native_analyzer.repo_path / "invalid-ca.pem"
    certificate.write_text("not a certificate", encoding="utf-8")
    monkeypatch.setenv("SSL_CERT_FILE", str(certificate))
    if owner == "analyzer":
        assert native_analyzer._run_semgrep_patterns(native_source) == []
    else:
        converter = OpenAPITestConverter(native_analyzer.repo_path, semgrep_config=native_analyzer.semgrep_config)
        assert converter._run_semgrep(native_source) == []
