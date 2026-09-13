"""Release review regressions exercise installed discovery and child imports."""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from specfact_code_review.run import runner


@pytest.mark.parametrize("actions", ["true", "false"])
def test_shallow_install_reaches_official_payload(monkeypatch: pytest.MonkeyPatch, actions: str) -> None:
    monkeypatch.setattr(runner, "__file__", "/src/specfact_code_review/run/runner.py")
    monkeypatch.setenv("GITHUB_ACTIONS", actions)
    installed = SimpleNamespace(status="PASS")
    monkeypatch.setattr(runner, "_official_installed_payload", lambda: (installed, ""))
    monkeypatch.setattr(runner, "_protected_candidate_payload", lambda: pytest.fail("not a source checkout"))
    assert runner._selected_module_payload().payload is installed


def test_sealed_pytest_imports_snapshot_before_project_dependency(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    roots = {name: tmp_path / name for name in ("analyzers", "builtin", "project", "snapshot")}
    for path in roots.values():
        path.mkdir()
    # This trusted pytest stub imports customer code after the actual observer's
    # startup. Decoys detect both project precedence and reserved-name shadowing.
    (roots["analyzers"] / "pytest.py").write_text(
        "def main(args, plugins):\n"
        "    import customer_module, specfact_code_review, reserved_dependency\n"
        "    assert customer_module.ORIGIN == 'snapshot'\n"
        "    assert specfact_code_review.ORIGIN == 'builtin'\n"
        "    assert reserved_dependency.ORIGIN == 'analyzers'\n"
        "    return 0\n"
    )
    cov = roots["analyzers"] / "pytest_cov"
    cov.mkdir()
    (cov / "__init__.py").write_text("")
    (cov / "plugin.py").write_text("")
    (roots["analyzers"] / "reserved_dependency.py").write_text("ORIGIN = 'analyzers'\n")
    (roots["builtin"] / "specfact_code_review.py").write_text("ORIGIN = 'builtin'\n")
    (roots["project"] / "customer_module.py").write_text("ORIGIN = 'project'\n")
    for name in ("customer_module", "specfact_code_review", "reserved_dependency"):
        (roots["snapshot"] / f"{name}.py").write_text("ORIGIN = 'snapshot'\n")
    (roots["snapshot"] / "pytest.py").write_text("raise RuntimeError('snapshot shadowed pytest')\n")
    monkeypatch.setattr(runner, "_pytest_in_capsule", lambda: True)
    monkeypatch.chdir(roots["snapshot"])
    script = runner._pytest_observer_script()
    for original, name in (
        ("/opt/specfact/analyzers", "analyzers"),
        ("/opt/specfact/builtin", "builtin"),
        ("/opt/specfact/project-runtime/site-packages", "project"),
    ):
        script = script.replace(original, str(roots[name]))
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", script, str(tmp_path / "observer.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
