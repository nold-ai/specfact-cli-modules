from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from specfact_code_review.ledger.client import LedgerClient, _default_local_path
from specfact_code_review.run.findings import PR_RANGE_ANALYZERS, AssuranceStatus, ReviewFinding, ReviewReport


class _Response:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


def _complete_analyzer_evidence(outcome: AssuranceStatus) -> list[dict[str, object]]:
    return [
        {"id": member_id, "execution_state": "ran", "evidence_outcome": outcome} for member_id in PR_RANGE_ANALYZERS
    ]


def _report(
    *,
    run_id: str = "run-001",
    score: int = 85,
    findings: list[ReviewFinding] | None = None,
) -> ReviewReport:
    return ReviewReport(
        run_id=run_id,
        timestamp=datetime(2026, 3, 16, tzinfo=UTC),
        score=score,
        findings=findings or [],
        summary="Review report for ledger tests.",
    )


def _blocking_finding() -> ReviewFinding:
    return ReviewFinding(
        category="architecture",
        severity="error",
        tool="pylint",
        rule="W0702",
        file="packages/specfact-code-review/src/specfact_code_review/review/commands.py",
        line=12,
        message="Blocking governance issue.",
        fixable=False,
    )


def _write_state(path: Path, *, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_record_run_with_supabase_available_inserts_row(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    posts: list[tuple[str, dict[str, Any]]] = []

    def fake_get(url: str, **_: Any) -> _Response:
        assert url.endswith("/rest/v1/reward_ledger")
        return _Response([])

    def fake_post(url: str, **kwargs: Any) -> _Response:
        posts.append((url, kwargs))
        return _Response([{"ok": True}])

    monkeypatch.setattr("specfact_code_review.ledger.client.requests.get", fake_get)
    monkeypatch.setattr("specfact_code_review.ledger.client.requests.post", fake_post)

    client = LedgerClient(
        supabase_url="https://example.supabase.co",
        supabase_key="service-role",
        local_path=tmp_path / "ledger.json",
    )

    status = client.record_run(_report())

    assert len(posts) == 2
    assert posts[0][0].endswith("/rest/v1/review_runs")
    assert posts[1][0].endswith("/rest/v1/reward_ledger")
    ledger_payload = posts[1][1]["json"]
    assert ledger_payload["cumulative_coins"] == pytest.approx(0.5)
    assert ledger_payload["streak_pass"] == 1
    assert status["coins"] == pytest.approx(0.5)


def test_record_run_without_supabase_writes_to_local_json(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    client = LedgerClient(local_path=ledger_path)

    status = client.record_run(_report())
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))

    assert payload["runs"][0]["session_id"] == "run-001"
    assert payload["runs"][0]["verdict"] == "PASS"
    assert status["coins"] == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("assurance_status", "reward_delta", "pass_streak", "block_streak"),
    [
        ("PASS", 5, 1, 0),
        ("FAIL", -5, 0, 1),
        ("UNKNOWN", 0, 0, 0),
        ("NOT_APPLICABLE", 0, 0, 0),
    ],
)
def test_ledger_authoritative_assurance_controls_rewards_and_streaks(
    tmp_path: Path,
    assurance_status: AssuranceStatus,
    reward_delta: int,
    pass_streak: int,
    block_streak: int,
) -> None:
    ledger_path = tmp_path / "ledger.json"
    report = ReviewReport(
        schema_version="1.6",
        assurance_status=assurance_status,
        run_id=f"run-{assurance_status.lower()}",
        timestamp=datetime(2026, 8, 19, tzinfo=UTC),
        score=85 if assurance_status == "PASS" else 75 if assurance_status == "FAIL" else 80,
        findings=[] if assurance_status != "FAIL" else [_blocking_finding()],
        summary=f"{assurance_status} evidence",
        overall_verdict="FAIL" if assurance_status in {"FAIL", "UNKNOWN"} else "PASS",
        ci_exit_code=1 if assurance_status in {"FAIL", "UNKNOWN"} else 0,
        scope_evidence={"assurance_kind": "range_candidate"},
        analyzer_evidence=_complete_analyzer_evidence(assurance_status),
    )

    LedgerClient(local_path=ledger_path).record_run(report)
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    run = payload["runs"][0]

    assert run["verdict"] == assurance_status
    assert run["reward_delta"] == reward_delta
    assert payload["streak_pass"] == pass_streak
    assert payload["streak_block"] == block_streak
    assert run["report_digest"].startswith("sha256:")
    assert run["report_json"]["assurance_status"] == assurance_status


def test_schema_1_6_missing_assurance_status_defaults_to_unknown(tmp_path: Path) -> None:
    report = ReviewReport.model_construct(
        schema_version="1.6",
        assurance_status=None,
        overall_verdict="PASS",
        findings=[],
    )

    client = LedgerClient(local_path=tmp_path / "ledger.json")

    assert client._verdict_for(report) == "UNKNOWN"
    assert client._reward_delta_for(report) == 0


def test_schema_1_6_known_outcome_preserves_report_reward_delta(tmp_path: Path) -> None:
    report = ReviewReport(
        schema_version="1.6",
        assurance_status="PASS",
        run_id="run-score-derived-reward",
        timestamp=datetime(2026, 8, 19, tzinfo=UTC),
        score=120,
        reward_delta=40,
        findings=[],
        summary="authoritative pass",
        overall_verdict="PASS",
        ci_exit_code=0,
        scope_evidence={"assurance_kind": "range_candidate"},
        analyzer_evidence=_complete_analyzer_evidence("PASS"),
    )

    assert LedgerClient(local_path=tmp_path / "ledger.json")._reward_delta_for(report) == 40


def test_record_run_applies_pass_streak_bonus_at_five(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    _write_state(
        ledger_path,
        payload={
            "agent": "claude-code",
            "cumulative_coins": 1.0,
            "streak_pass": 4,
            "streak_block": 0,
            "last_delta": 5,
            "last_verdict": "PASS",
            "violation_counts": {},
            "runs": [],
        },
    )
    client = LedgerClient(local_path=ledger_path)

    status = client.record_run(_report(run_id="run-005", score=85))

    assert status["coins"] == pytest.approx(2.0)
    assert status["streak_pass"] == 5


def test_record_run_applies_block_streak_penalty_at_three(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    _write_state(
        ledger_path,
        payload={
            "agent": "claude-code",
            "cumulative_coins": 2.0,
            "streak_pass": 0,
            "streak_block": 2,
            "last_delta": 0,
            "last_verdict": "FAIL",
            "violation_counts": {"W0702": 2},
            "runs": [],
        },
    )
    client = LedgerClient(local_path=ledger_path)

    status = client.record_run(_report(run_id="run-006", score=80, findings=[_blocking_finding()]))

    assert status["coins"] == pytest.approx(1.0)
    assert status["streak_block"] == 3
    assert status["last_verdict"] == "FAIL"


def test_get_status_returns_correct_dict(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    _write_state(
        ledger_path,
        payload={
            "agent": "claude-code",
            "cumulative_coins": 12.5,
            "streak_pass": 3,
            "streak_block": 0,
            "last_delta": 5,
            "last_verdict": "PASS",
            "violation_counts": {"E501": 4, "W0702": 2},
            "runs": [],
        },
    )
    client = LedgerClient(local_path=ledger_path)

    status = client.get_status()

    assert status["coins"] == pytest.approx(12.5)
    assert status["streak_pass"] == 3
    assert status["last_verdict"] == "PASS"


def test_record_run_uses_reward_delta_divided_by_ten(tmp_path: Path) -> None:
    client = LedgerClient(local_path=tmp_path / "ledger.json")

    status = client.record_run(_report(run_id="run-007", score=87))

    assert status["coins"] == pytest.approx(0.7)


def test_get_status_falls_back_when_local_payload_is_invalid(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text('{"runs": "invalid"}', encoding="utf-8")
    client = LedgerClient(local_path=ledger_path)

    status = client.get_status()

    assert status["coins"] == pytest.approx(0.0)
    assert status["last_verdict"] == "UNKNOWN"


def test_default_local_path_uses_explicit_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    explicit = tmp_path / "custom-ledger.json"
    monkeypatch.setenv("SPECFACT_LEDGER_PATH", str(explicit))

    assert _default_local_path() == explicit


def test_get_status_falls_back_when_supabase_state_is_invalid(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get(*_args: Any, **_kwargs: Any) -> _Response:
        return _Response([{"agent": "claude-code", "last_verdict": object()}])

    monkeypatch.setattr("specfact_code_review.ledger.client.requests.get", fake_get)
    client = LedgerClient(
        supabase_url="https://example.supabase.co",
        supabase_key="service-role",
        local_path=tmp_path / "ledger.json",
    )

    status = client.get_status()

    assert status["coins"] == pytest.approx(0.0)
    assert status["last_verdict"] == "UNKNOWN"


def test_get_recent_runs_returns_empty_when_supabase_runs_are_invalid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_get(*_args: Any, **_kwargs: Any) -> _Response:
        return _Response([{"session_id": "run-1"}])

    monkeypatch.setattr("specfact_code_review.ledger.client.requests.get", fake_get)
    client = LedgerClient(
        supabase_url="https://example.supabase.co",
        supabase_key="service-role",
        local_path=tmp_path / "ledger.json",
    )

    assert not client.get_recent_runs()


def test_reset_local_returns_true_when_file_is_missing(tmp_path: Path) -> None:
    client = LedgerClient(local_path=tmp_path / "missing.json")

    assert client.reset_local() is True
