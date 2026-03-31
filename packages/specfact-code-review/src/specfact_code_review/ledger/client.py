"""Reward-ledger persistence with Supabase-first and local JSON fallback."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypedDict

import requests
from beartype import beartype
from icontract import ensure, require
from pydantic import BaseModel, Field, ValidationError

from specfact_code_review.run.findings import FAIL, ReviewFinding, ReviewReport


LedgerVerdict = Literal["PASS", "PASS_WITH_ADVISORY", "FAIL"]
DEFAULT_AGENT = "claude-code"
DEFAULT_LOCAL_PATH = Path.home() / ".specfact" / "ledger.json"


class LedgerStatus(TypedDict):
    """Public ledger status payload returned to CLI commands."""

    coins: float
    streak_pass: int
    streak_block: int
    last_verdict: str
    top_violations: list[tuple[str, int]]


class LedgerRun(BaseModel):
    """Persisted review-run payload."""

    session_id: str = Field(..., description="Stable run identifier.")
    issue_number: int | None = Field(default=None, description="Optional linked issue number.")
    agent: str = Field(default=DEFAULT_AGENT, description="Agent name.")
    changed_files: list[str] = Field(default_factory=list, description="Changed files captured in the run.")
    score: int = Field(..., ge=0, le=120, description="Governed review score.")
    reward_delta: int = Field(..., description="Raw reward delta from ReviewReport.")
    verdict: LedgerVerdict = Field(..., description="Overall review verdict.")
    findings_json: list[dict[str, Any]] = Field(default_factory=list, description="Serialized findings payload.")
    house_rules_ver: int = Field(default=1, description="House-rules version observed during the run.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="UTC creation timestamp.")


class LedgerState(BaseModel):
    """Current reward-ledger state."""

    agent: str = Field(default=DEFAULT_AGENT, description="Agent name.")
    cumulative_coins: float = Field(default=0.0, description="Accumulated reward coins.")
    streak_pass: int = Field(default=0, ge=0, description="Current passing streak length.")
    streak_block: int = Field(default=0, ge=0, description="Current blocking streak length.")
    last_delta: int = Field(default=0, description="Most recent raw reward delta.")
    last_verdict: LedgerVerdict | None = Field(default=None, description="Most recent review verdict.")
    violation_counts: dict[str, int] = Field(default_factory=dict, description="Aggregated rule counts.")
    runs: list[LedgerRun] = Field(default_factory=list, description="Locally persisted runs.")


class LedgerClient:
    """Persist review-run rewards to Supabase with a local JSON fallback."""

    def __init__(
        self,
        *,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        local_path: Path | None = None,
        agent: str = DEFAULT_AGENT,
    ) -> None:
        self._supabase_url = (supabase_url or "").rstrip("/")
        self._supabase_key = supabase_key or ""
        self._local_path = local_path or _default_local_path()
        self._agent = agent

    @beartype
    @require(lambda report: isinstance(report, ReviewReport), "report must be a ReviewReport")
    @ensure(lambda result: isinstance(result, dict), "record_run must return a status dictionary")
    def record_run(self, report: ReviewReport) -> LedgerStatus:
        """Record a review run and return the updated ledger status."""
        current_state = self._read_supabase_state() if self._supabase_enabled else None
        if current_state is None:
            current_state = self._read_local_state()

        updated_state, run_entry = self._apply_report(current_state, report)
        if self._supabase_enabled and self._write_supabase(run_entry, updated_state):
            return self._status_payload(updated_state)

        self._write_local_state(updated_state)
        return self._status_payload(updated_state)

    @beartype
    @ensure(lambda result: isinstance(result, dict), "get_status must return a status dictionary")
    def get_status(self) -> LedgerStatus:
        """Return the current ledger status from Supabase or the local fallback."""
        state = self._read_supabase_state()
        if state is None:
            state = self._read_local_state()
        return self._status_payload(state)

    @beartype
    @ensure(lambda result: isinstance(result, list), "get_recent_runs must return a list")
    def get_recent_runs(self, *, limit: int = 20) -> list[LedgerRun]:
        """Return the most recent persisted review runs."""
        runs = self._read_supabase_runs(limit=limit) if self._supabase_enabled else None
        if runs is None:
            runs = self._read_local_state().runs[-limit:]
        return list(runs)

    @beartype
    @ensure(lambda result: isinstance(result, bool), "reset_local must return a boolean")
    def reset_local(self) -> bool:
        """Delete the local fallback ledger if it exists."""
        if self._local_path.exists():
            self._local_path.unlink()
        return True

    @property
    def _supabase_enabled(self) -> bool:
        return bool(self._supabase_url and self._supabase_key)

    def _apply_report(self, current_state: LedgerState, report: ReviewReport) -> tuple[LedgerState, LedgerRun]:
        run_entry = LedgerRun(
            session_id=report.run_id,
            agent=self._agent,
            changed_files=self._changed_files_for(report),
            score=report.score,
            reward_delta=report.reward_delta or 0,
            verdict=self._verdict_for(report),
            findings_json=[finding.model_dump(mode="json") for finding in report.findings],
            created_at=report.timestamp,
        )
        next_pass_streak = current_state.streak_pass + 1 if run_entry.verdict != FAIL else 0
        next_block_streak = current_state.streak_block + 1 if run_entry.verdict == FAIL else 0

        coin_delta = (run_entry.reward_delta or 0) / 10.0
        if run_entry.verdict != FAIL and next_pass_streak >= 5:
            coin_delta += 0.5
        if run_entry.verdict == FAIL and next_block_streak >= 3:
            coin_delta -= 1.0

        violation_counts = Counter(current_state.violation_counts)
        violation_counts.update(self._rule_counts(report.findings))

        updated_state = LedgerState(
            agent=self._agent,
            cumulative_coins=round(current_state.cumulative_coins + coin_delta, 2),
            streak_pass=next_pass_streak,
            streak_block=next_block_streak,
            last_delta=run_entry.reward_delta,
            last_verdict=run_entry.verdict,
            violation_counts=dict(violation_counts),
            runs=[*current_state.runs, run_entry],
        )
        return updated_state, run_entry

    def _changed_files_for(self, report: ReviewReport) -> list[str]:
        return sorted({finding.file for finding in report.findings if finding.file})

    def _verdict_for(self, report: ReviewReport) -> LedgerVerdict:
        if report.overall_verdict is None:
            return "PASS_WITH_ADVISORY"
        return report.overall_verdict

    def _rule_counts(self, findings: list[ReviewFinding]) -> Counter[str]:
        return Counter(finding.rule for finding in findings)

    def _read_local_state(self) -> LedgerState:
        if not self._local_path.exists():
            return LedgerState(agent=self._agent)
        try:
            payload = json.loads(self._local_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return LedgerState(agent=self._agent)
        try:
            return LedgerState.model_validate(payload)
        except ValidationError:
            return LedgerState(agent=self._agent)

    def _write_local_state(self, state: LedgerState) -> None:
        self._local_path.parent.mkdir(parents=True, exist_ok=True)
        self._local_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def _ledger_run_from_payload_entry(self, entry: object) -> LedgerRun | None:
        if not isinstance(entry, dict):
            return None
        try:
            return LedgerRun.model_validate(entry)
        except ValidationError:
            return None

    def _read_supabase_runs(self, *, limit: int) -> list[LedgerRun] | None:
        try:
            response = requests.get(
                f"{self._supabase_url}/rest/v1/review_runs",
                headers=self._supabase_headers(),
                params={
                    "agent": f"eq.{self._agent}",
                    "order": "created_at.desc",
                    "limit": str(limit),
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return None

        if not isinstance(payload, list):
            return None

        runs: list[LedgerRun] = []
        for entry in reversed(payload):
            run = self._ledger_run_from_payload_entry(entry)
            if run is None:
                return None
            runs.append(run)
        return runs

    def _read_supabase_state(self) -> LedgerState | None:
        if not self._supabase_enabled:
            return None
        try:
            response = requests.get(
                f"{self._supabase_url}/rest/v1/reward_ledger",
                headers=self._supabase_headers(),
                params={
                    "agent": f"eq.{self._agent}",
                    "order": "updated_at.desc",
                    "limit": "1",
                },
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return None

        if not isinstance(payload, list) or not payload:
            return LedgerState(agent=self._agent)

        latest_row = payload[0]
        if not isinstance(latest_row, dict):
            return LedgerState(agent=self._agent)
        try:
            return LedgerState(
                agent=str(latest_row.get("agent", self._agent)),
                cumulative_coins=float(latest_row.get("cumulative_coins", 0.0)),
                streak_pass=int(latest_row.get("streak_pass", 0)),
                streak_block=int(latest_row.get("streak_block", 0)),
                last_delta=int(latest_row.get("last_delta", 0) or 0),
                last_verdict=latest_row.get("last_verdict"),
                violation_counts={},
                runs=[],
            )
        except (TypeError, ValueError, ValidationError):
            return LedgerState(agent=self._agent)

    def _write_supabase(self, run_entry: LedgerRun, state: LedgerState) -> bool:
        try:
            run_response = requests.post(
                f"{self._supabase_url}/rest/v1/review_runs",
                headers=self._supabase_headers(prefer_representation=True),
                json=run_entry.model_dump(mode="json"),
                timeout=10,
            )
            run_response.raise_for_status()
            ledger_response = requests.post(
                f"{self._supabase_url}/rest/v1/reward_ledger",
                headers=self._supabase_headers(prefer_representation=True),
                json={
                    "agent": state.agent,
                    "session_id": run_entry.session_id,
                    "cumulative_coins": state.cumulative_coins,
                    "last_delta": state.last_delta,
                    "last_verdict": state.last_verdict,
                    "streak_pass": state.streak_pass,
                    "streak_block": state.streak_block,
                    "updated_at": datetime.now(UTC).isoformat(),
                },
                timeout=10,
            )
            ledger_response.raise_for_status()
        except requests.RequestException:
            return False
        return True

    def _supabase_headers(self, *, prefer_representation: bool = False) -> dict[str, str]:
        headers = {
            "apikey": self._supabase_key,
            "Authorization": f"Bearer {self._supabase_key}",
            "Content-Type": "application/json",
        }
        if prefer_representation:
            headers["Prefer"] = "return=representation"
        return headers

    def _status_payload(self, state: LedgerState) -> LedgerStatus:
        top_violations = sorted(state.violation_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
        return {
            "coins": round(state.cumulative_coins, 2),
            "streak_pass": state.streak_pass,
            "streak_block": state.streak_block,
            "last_verdict": state.last_verdict or "UNKNOWN",
            "top_violations": top_violations,
        }


def _default_local_path() -> Path:
    explicit = os.environ.get("SPECFACT_LEDGER_PATH", "").strip()
    if explicit:
        return Path(explicit).expanduser()

    start = Path.cwd().resolve()
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate / ".specfact" / "ledger.json"
    return DEFAULT_LOCAL_PATH
