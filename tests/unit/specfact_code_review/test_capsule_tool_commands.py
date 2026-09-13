"""Child analyzer commands retain sealed startup and private writable state."""

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
