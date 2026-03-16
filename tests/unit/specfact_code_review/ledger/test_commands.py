from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from specfact_code_review.review.commands import app
from specfact_code_review.run.findings import ReviewReport


runner = CliRunner()


def _report_json() -> str:
    report = ReviewReport(
        run_id="run-commands-001",
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=85,
        findings=[],
        summary="Command test report.",
    )
    return report.model_dump_json()


def test_ledger_update_reads_valid_json_stdin_and_calls_record_run(monkeypatch: Any) -> None:
    recorded: dict[str, ReviewReport] = {}

    class FakeLedgerClient:
        def record_run(self, report: ReviewReport) -> dict[str, object]:
            recorded["report"] = report
            return {"coins": 0.5, "streak_pass": 1, "streak_block": 0, "last_verdict": "PASS", "top_violations": []}

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "update"], input=_report_json())

    assert result.exit_code == 0
    assert recorded["report"].run_id == "run-commands-001"


def test_ledger_update_reads_valid_json_from_file(monkeypatch: Any, tmp_path: Path) -> None:
    recorded: dict[str, ReviewReport] = {}
    report_file = tmp_path / "review-report.json"
    report_file.write_text(_report_json(), encoding="utf-8")

    class FakeLedgerClient:
        def record_run(self, report: ReviewReport) -> dict[str, object]:
            recorded["report"] = report
            return {"coins": 0.5, "streak_pass": 1, "streak_block": 0, "last_verdict": "PASS", "top_violations": []}

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "update", "--from", str(report_file)])

    assert result.exit_code == 0
    assert recorded["report"].run_id == "run-commands-001"


def test_ledger_update_with_invalid_json_exits_with_error(monkeypatch: Any) -> None:
    class FakeLedgerClient:
        def record_run(self, report: ReviewReport) -> dict[str, object]:
            raise AssertionError("record_run should not be called")

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "update"], input="{not-json")

    assert result.exit_code == 1
    assert "Invalid ReviewReport JSON" in result.output


def test_ledger_status_prints_current_state(monkeypatch: Any) -> None:
    class FakeLedgerClient:
        def get_status(self) -> dict[str, object]:
            return {
                "coins": 7.3,
                "streak_pass": 2,
                "streak_block": 0,
                "last_verdict": "PASS",
                "top_violations": [("E501", 3), ("W0702", 1)],
            }

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "status"])

    assert result.exit_code == 0
    assert "7.30" in result.output
    assert "2" in result.output
    assert "PASS" in result.output


def test_ledger_status_renders_top_violations_from_dict_entries(monkeypatch: Any) -> None:
    class FakeLedgerClient:
        def get_status(self) -> dict[str, object]:
            return {
                "coins": 7.3,
                "streak_pass": 2,
                "streak_block": 0,
                "last_verdict": "PASS",
                "top_violations": [{"rule": "E501", "count": 3}],
            }

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "status"])

    assert result.exit_code == 0
    assert "E501 (3)" in result.output


def test_ledger_update_surfaces_write_errors(monkeypatch: Any) -> None:
    class FakeLedgerClient:
        def record_run(self, report: ReviewReport) -> dict[str, object]:
            raise OSError("disk full")

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "update"], input=_report_json())

    assert result.exit_code == 1
    assert "Unable to write ledger state" in result.output


def test_ledger_status_surfaces_read_errors(monkeypatch: Any) -> None:
    class FakeLedgerClient:
        def get_status(self) -> dict[str, object]:
            raise OSError("permission denied")

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "status"])

    assert result.exit_code == 1
    assert "Unable to read ledger state" in result.output


def test_ledger_reset_without_confirm_refuses_deletion(monkeypatch: Any) -> None:
    called = {"reset": False}

    class FakeLedgerClient:
        def reset_local(self) -> bool:
            called["reset"] = True
            return True

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "reset"])

    assert result.exit_code == 1
    assert "--confirm" in result.output
    assert called["reset"] is False


def test_ledger_reset_with_confirm_clears_local_ledger(monkeypatch: Any) -> None:
    called = {"reset": False}

    class FakeLedgerClient:
        def reset_local(self) -> bool:
            called["reset"] = True
            return True

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "reset", "--confirm"])

    assert result.exit_code == 0
    assert called["reset"] is True


def test_ledger_reset_surfaces_delete_errors(monkeypatch: Any) -> None:
    class FakeLedgerClient:
        def reset_local(self) -> bool:
            raise OSError("readonly")

    monkeypatch.setattr("specfact_code_review.ledger.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "ledger", "reset", "--confirm"])

    assert result.exit_code == 1
    assert "Unable to reset ledger state" in result.output
