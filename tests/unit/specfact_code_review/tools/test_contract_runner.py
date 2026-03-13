from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock

from pytest import MonkeyPatch

from specfact_code_review.tools.contract_runner import run_contract_check
from tests.unit.specfact_code_review.tools.helpers import assert_tool_run, completed_process


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "contract_runner"


def test_run_contract_check_reports_public_function_without_contracts(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_without_contracts.py"
    run_mock = Mock(return_value=completed_process("crosshair", stdout=""))
    monkeypatch.setattr(subprocess, "run", run_mock)

    findings = run_contract_check([file_path])

    assert len(findings) == 1
    assert findings[0].category == "contracts"
    assert findings[0].rule == "MISSING_ICONTRACT"
    assert findings[0].file == str(file_path)
    assert findings[0].line == 1
    assert_tool_run(run_mock, ["crosshair", "check", "--per_path_timeout", "2", str(file_path)])


def test_run_contract_check_skips_decorated_public_function(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_with_contracts.py"
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("crosshair", stdout="")))

    findings = run_contract_check([file_path])

    assert findings == []


def test_run_contract_check_skips_private_function(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "private_only.py"
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process("crosshair", stdout="")))

    findings = run_contract_check([file_path])

    assert findings == []


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


def test_run_contract_check_ignores_crosshair_timeout(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_with_contracts.py"
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(side_effect=subprocess.TimeoutExpired(cmd="crosshair", timeout=30)),
    )

    findings = run_contract_check([file_path])

    assert findings == []


def test_run_contract_check_reports_unavailable_crosshair_but_keeps_ast_findings(monkeypatch: MonkeyPatch) -> None:
    file_path = FIXTURES_DIR / "public_without_contracts.py"
    monkeypatch.setattr(subprocess, "run", Mock(side_effect=FileNotFoundError("crosshair not found")))

    findings = run_contract_check([file_path])

    assert len(findings) == 2
    assert {finding.category for finding in findings} == {"contracts", "tool_error"}
    assert {finding.tool for finding in findings} == {"contract_runner", "crosshair"}
    crosshair_finding = next(finding for finding in findings if finding.tool == "crosshair")
    assert crosshair_finding.severity == "warning"
