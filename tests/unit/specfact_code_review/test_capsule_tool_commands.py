"""Child analyzer commands retain sealed startup and private writable state."""

from pathlib import Path

import pytest

from specfact_code_review import _review_utils


@pytest.mark.parametrize(
    "tool,module",
    [
        ("radon", "radon"),
        ("pylint", "pylint"),
        ("basedpyright", "basedpyright"),
        ("crosshair", "crosshair"),
        ("semgrep", "semgrep.console_scripts.pysemgrep"),
    ],
)
def test_capsule_python_child_reenters_sealed_bootstrap(
    monkeypatch: pytest.MonkeyPatch, tool: str, module: str
) -> None:
    """A Python console entrypoint must not lose the verified analyzer import root."""
    monkeypatch.setattr(_review_utils, "__file__", "/opt/specfact/builtin/specfact_code_review/_review_utils.py")
    command = _review_utils.analyzer_command([tool, "--version"])
    assert command == [
        "/opt/specfact/python/bin/python",
        "-I",
        "-S",
        "/opt/specfact/bootstrap/sealed_bootstrap.py",
        module,
        "--version",
    ]


def test_capsule_ruff_cache_stays_in_private_mount(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ruff cannot create its default cache beneath the read-only snapshot."""
    monkeypatch.setattr(_review_utils, "__file__", "/opt/specfact/builtin/specfact_code_review/_review_utils.py")
    command = _review_utils.analyzer_command(["ruff", "check", "example.py"])
    assert command == ["ruff", "check", "example.py", "--cache-dir", "/opt/specfact/tmp/cache/ruff"]


def test_host_tool_commands_keep_existing_behavior() -> None:
    """Ordinary compatibility execution keeps the caller's executable and flags."""
    for command in (["pylint", "example.py"], ["ruff", "check", "example.py"]):
        assert _review_utils.analyzer_command(command) == command


def test_development_snapshot_uses_its_verified_runtime_without_leaking_context() -> None:
    from specfact_code_review._review_utils import analyzer_command, development_runtime

    original = ["basedpyright", "--outputjson", "src/app.py"]
    with development_runtime(Path("/private/development/.venv")):
        command = analyzer_command(original)
        assert "--venvpath" not in command
        assert command[command.index("--pythonpath") + 1] == "/private/development/.venv/bin/python"
    assert analyzer_command(original) == original


def test_development_context_runs_basedpyright_with_import_resolution(tmp_path) -> None:
    import json
    import subprocess
    import sys

    source = tmp_path / "app.py"
    source.write_text(
        "from icontract import require\n@require(lambda x: x > 0)\ndef positive(x: int) -> int:\n    return x\n"
    )
    with _review_utils.development_runtime(Path(sys.prefix)):
        command = _review_utils.analyzer_command(["basedpyright", "--outputjson", str(source)])
    result = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True, check=False)
    assert result.returncode in (0, 1), result.stderr
    report = json.loads(result.stdout)
    assert not [item for item in report["generalDiagnostics"] if item["severity"] == "error"]
