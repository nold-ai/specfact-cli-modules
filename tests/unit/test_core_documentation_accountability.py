from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit._script_test_utils import load_module_from_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check-core-documentation-accountability.py"


def _load_script():
    return load_module_from_path("check_core_documentation_accountability", SCRIPT_PATH)


def _core_checkout(tmp_path: Path) -> Path:
    checker = tmp_path / "scripts" / "check-documentation-accountability.py"
    checker.parent.mkdir(parents=True)
    checker.write_text("raise SystemExit(0)\n", encoding="utf-8")
    return tmp_path


def test_resolve_core_checkout_prefers_explicit_environment_path(tmp_path: Path, monkeypatch) -> None:
    script = _load_script()
    core_root = _core_checkout(tmp_path / "core")
    monkeypatch.setenv("SPECFACT_CLI_REPO", str(core_root))

    assert script.resolve_core_checkout() == core_root.resolve()


@pytest.mark.parametrize(
    ("modules_relative", "core_relative"),
    (
        (Path("specfact-cli-modules"), Path("specfact-cli")),
        (
            Path("specfact-cli-modules-worktrees") / "feature" / "docs-16",
            Path("specfact-cli-worktrees") / "feature" / "docs-16",
        ),
    ),
)
def test_resolve_core_checkout_uses_documented_local_fallbacks(
    tmp_path: Path, monkeypatch, modules_relative: Path, core_relative: Path
) -> None:
    script = _load_script()
    modules_root = tmp_path / modules_relative
    modules_root.mkdir(parents=True)
    core_root = _core_checkout(tmp_path / core_relative)
    monkeypatch.delenv("SPECFACT_CLI_REPO", raising=False)
    monkeypatch.setattr(script, "REPO_ROOT", modules_root)

    assert script.resolve_core_checkout() == core_root.resolve()


def test_resolve_core_checkout_fails_closed_with_setup_guidance(tmp_path: Path, monkeypatch) -> None:
    script = _load_script()
    monkeypatch.setenv("SPECFACT_CLI_REPO", str(tmp_path / "missing"))
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path / "modules")

    with pytest.raises(ValueError, match="Set SPECFACT_CLI_REPO"):
        script.resolve_core_checkout()


def test_run_accountability_propagates_core_checker_failure(tmp_path: Path, monkeypatch) -> None:
    script = _load_script()
    core_root = _core_checkout(tmp_path / "core")
    modules_root = tmp_path / "modules"
    modules_root.mkdir()
    calls: list[list[str]] = []

    class _Result:
        returncode = 7

    def fake_run(command: list[str], check: bool) -> _Result:
        calls.append(command)
        assert check is False
        return _Result()

    monkeypatch.setattr(script.subprocess, "run", fake_run)

    assert script.run_accountability(core_root, modules_root) == 7
    assert calls == [
        [
            script.sys.executable,
            str(core_root / "scripts" / "check-documentation-accountability.py"),
            "--modules-repo",
            str(modules_root.resolve()),
        ]
    ]
