from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

from specfact_code_review.tools.contract_runner import _skip_icontract_ast_scan, run_contract_check
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "contract_runner"


@pytest.fixture(autouse=True)
def _stub_crosshair_on_path(monkeypatch: MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    """So skip_if_tool_missing does not short-circuit before mocked subprocess.run."""
    real_which = shutil.which

    def _which(name: str) -> str | None:
        if name == "crosshair":
            return "/fake/crosshair"
        return real_which(name)

    monkeypatch.setattr("specfact_code_review.tools.tool_availability.shutil.which", _which)


def test_run_contract_check_skips_missing_icontract_when_package_unused(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    file_path = tmp_path / "public_without_contracts.py"
    file_path.write_text("def public_without_contracts(value: int) -> int:\n    return value + 1\n", encoding="utf-8")
    run_mock = Mock(return_value=completed_process("crosshair", stdout=""))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_contract_check([file_path])

    assert not findings
    assert_tool_run(run_mock, ["crosshair", "check", "--per_path_timeout", "2", str(file_path)])


def test_run_contract_check_uses_batch_level_icontract_detection(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """Icontract usage in a sibling module under the same bundle roots ``MISSING_ICONTRACT`` on the edited file."""
    (tmp_path / ".git").mkdir()
    pkg = tmp_path / "packages" / "demo_pkg"
    pkg.mkdir(parents=True)
    (pkg / "uses_icontract.py").write_text("import icontract\n", encoding="utf-8")
    tmp_file = pkg / "public_without_contracts.py"
    tmp_file.write_text(
        "def public_without_contracts(value: int) -> int:\n    return value + 1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("crosshair", stdout="")))

    findings = run_contract_check([tmp_file])

    assert "MISSING_ICONTRACT" in {finding.rule for finding in findings}


def test_run_contract_check_detects_icontract_across_package_bundles(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """MISSING_ICONTRACT must not depend only on the edited bundle: scan ``packages/`` when needed."""
    (tmp_path / ".git").mkdir()
    pkg_a = tmp_path / "packages" / "pkg_a"
    pkg_b = tmp_path / "packages" / "pkg_b"
    pkg_a.mkdir(parents=True)
    pkg_b.mkdir(parents=True)
    (pkg_b / "icontract_anchor.py").write_text("import icontract\n", encoding="utf-8")
    edited = pkg_a / "new_public_api.py"
    edited.write_text(
        "def public_no_contracts(value: int) -> int:\n    return value + 1\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("crosshair", stdout="")))

    findings = run_contract_check([edited])

    assert "MISSING_ICONTRACT" in {finding.rule for finding in findings}


def test_run_contract_check_skips_decorated_public_function(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_with_contracts.py"
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("crosshair", stdout="")))

    findings = run_contract_check([file_path])

    assert not findings


def test_run_contract_check_skips_private_function(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "private_only.py"
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("crosshair", stdout="")))

    findings = run_contract_check([file_path])

    assert not findings


def test_run_contract_check_maps_crosshair_counterexample(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_with_contracts.py"
    stdout = f"{file_path}:5: error: false when calling public_with_contracts(-1)\n"
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=completed_process("crosshair", stdout=stdout, returncode=1))
    )

    findings = run_contract_check([file_path])

    assert len(findings) == 1
    assert findings[0].category == "contracts"
    assert findings[0].severity == "warning"
    assert findings[0].tool == "crosshair"
    assert findings[0].line == 5


def test_run_contract_check_ignores_crosshair_side_effect_warnings(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_with_contracts.py"
    stdout = f'{file_path}:5: error: SideEffectDetected: A "subprocess.Popen" operation was detected.\n'
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=completed_process("crosshair", stdout=stdout, returncode=1))
    )

    findings = run_contract_check([file_path])

    assert not findings


def test_run_contract_check_ignores_crosshair_timeout(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_with_contracts.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(side_effect=subprocess.TimeoutExpired(cmd="crosshair", timeout=30)),
    )

    findings = run_contract_check([file_path])

    assert not findings


def test_run_contract_check_reports_unavailable_crosshair_but_keeps_ast_findings(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_missing_contract_but_icontract_imported.py"
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=FileNotFoundError("crosshair not found")))

    findings = run_contract_check([file_path])

    assert len(findings) == 2
    assert {finding.category for finding in findings} == {"contracts", "tool_error"}
    assert {finding.tool for finding in findings} == {"contract_runner", "crosshair"}
    crosshair_finding = next(finding for finding in findings if finding.tool == "crosshair")
    assert crosshair_finding.severity == "warning"


def test_run_contract_check_ignores_crosshair_findings_for_other_files(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_with_contracts.py"
    stdout = "/tmp/other.py:5: error: false when calling something()\n"
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=completed_process("crosshair", stdout=stdout, returncode=1))
    )

    findings = run_contract_check([file_path])

    assert not findings


def test_skip_icontract_ast_scan_skips_helper_modules() -> None:
    assert _skip_icontract_ast_scan(
        Path("packages/specfact-project/src/specfact_project/importers/speckit_markdown_sections.py")
    )
    assert _skip_icontract_ast_scan(
        Path("packages/specfact-project/src/specfact_project/sync_runtime/bridge_sync_extract_requirement_impl.py")
    )
    assert _skip_icontract_ast_scan(
        Path("packages/specfact-project/src/specfact_project/sync_runtime/sync_bridge_command_setup.py")
    )


def test_skip_icontract_ast_scan_keeps_public_sync_entrypoints() -> None:
    assert not _skip_icontract_ast_scan(
        Path("packages/specfact-project/src/specfact_project/sync_runtime/bridge_sync.py")
    )
    assert not _skip_icontract_ast_scan(
        Path("packages/specfact-project/src/specfact_project/sync_runtime/speckit_backlog_sync.py")
    )
