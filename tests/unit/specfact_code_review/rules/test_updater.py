from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from icontract.errors import ViolationError
from typer.testing import CliRunner

from specfact_code_review.ledger.client import LedgerRun
from specfact_code_review.review.commands import app
from specfact_code_review.rules.updater import (
    IDE_SKILL_PATHS,
    MAX_SKILL_LINES,
    SKILL_PATH,
    default_skill_content,
    load_bundled_skill_content,
    update_house_rules,
)


runner = CliRunner()


def _skill_text(
    *,
    version: int = 1,
    updated_on: str = "2026-03-10",
    top_rules: list[str] | None = None,
    extra_do_rules: list[str] | None = None,
) -> str:
    do_rules = [
        "- Keep functions under 120 LOC and cyclomatic complexity <= 12",
        "- Add @require/@ensure (icontract) + @beartype to all new public APIs",
        "- Run hatch run contract-test-contracts before any commit",
        "- Guard all chained attribute access: a.b.c needs null-check or early return",
        "- Return typed values from all public methods",
        "- Write the test file BEFORE the feature file (TDD-first)",
        "- Use get_logger(__name__) from common.logger_setup, never print()",
    ]
    if extra_do_rules:
        do_rules.extend(extra_do_rules)

    dont_rules = [
        "- Don't mix read + write in the same method; split responsibilities",
        "- Don't use bare except: or except Exception: pass",
        "- Don't add # noqa / # type: ignore without inline justification",
        "- Don't call repository.* and http_client.* in the same function",
        "- Don't import at module level if it triggers network calls",
        "- Don't hardcode secrets; use env vars via pydantic.BaseSettings",
        "- Don't create functions > 120 lines",
    ]

    lines = [
        "---",
        "name: specfact-code-review",
        "description: House rules for AI coding sessions derived from review findings",
        "allowed-tools: []",
        "---",
        "",
        f"# House Rules - AI Coding Context (v{version})",
        "",
        f"Updated: {updated_on} | Module: nold-ai/specfact-code-review",
        "",
        "## DO",
        *do_rules,
        "",
        "## DON'T",
        *dont_rules,
        "",
        "## TOP VIOLATIONS (auto-updated by specfact code review rules update)",
        "<!-- auto-managed: do not edit manually -->",
    ]
    if top_rules:
        lines.extend(top_rules)
    return "\n".join(lines) + "\n"


def _run(*rules: str, created_at: datetime | None = None) -> LedgerRun:
    when = created_at or datetime(2026, 3, 10, tzinfo=UTC)
    findings = [
        {
            "category": "clean_code",
            "severity": "warning",
            "tool": "ruff",
            "rule": rule,
            "file": "packages/specfact-code-review/src/specfact_code_review/run/runner.py",
            "line": 10,
            "message": f"{rule} finding",
            "fixable": False,
        }
        for rule in rules
    ]
    return LedgerRun(
        session_id=f"run-{when.isoformat()}",
        score=80,
        reward_delta=0,
        verdict="PASS",
        findings_json=findings,
        created_at=when,
    )


def test_load_bundled_skill_content_returns_valid_structure_when_available() -> None:
    """Bundled SKILL is used when package is installed; content has required sections."""
    content = load_bundled_skill_content()
    if content is None:
        pytest.skip("Bundled SKILL not found (e.g. package not installed)")
    assert "name: specfact-code-review" in content
    assert "## DO" in content
    assert "## DON'T" in content
    assert "## TOP VIOLATIONS" in content
    assert "<!-- auto-managed: do not edit manually -->" in content
    assert len(content.splitlines()) <= MAX_SKILL_LINES


def test_default_skill_content_stays_within_line_budget() -> None:
    skill = default_skill_content(updated_on=date(2026, 3, 10))

    assert len(skill.splitlines()) <= MAX_SKILL_LINES
    assert "name: specfact-code-review" in skill
    assert "allowed-tools: []" in skill


def test_update_house_rules_surfaces_rule_with_three_hits(tmp_path: Path) -> None:
    skill_path = tmp_path / "skills/specfact-code-review/SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(_skill_text(), encoding="utf-8")

    runs = [_run("C901"), _run("C901"), _run("C901"), _run("T201")]

    updated = update_house_rules(skill_path, runs, updated_on=date(2026, 3, 16))

    assert "- C901 (3 hits in last 20 runs)" in updated


def test_update_house_rules_does_not_add_rule_below_threshold(tmp_path: Path) -> None:
    skill_path = tmp_path / "skills/specfact-code-review/SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(_skill_text(), encoding="utf-8")

    updated = update_house_rules(skill_path, [_run("T201"), _run("T201")], updated_on=date(2026, 3, 16))

    assert "- T201 (2 hits in last 20 runs)" not in updated


def test_update_house_rules_prunes_rule_missing_for_ten_runs(tmp_path: Path) -> None:
    skill_path = tmp_path / "skills/specfact-code-review/SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(_skill_text(top_rules=["- W0702 (4 hits in last 20 runs)"]), encoding="utf-8")

    runs = [_run("C901", created_at=datetime(2026, 3, 1, tzinfo=UTC) + timedelta(days=index)) for index in range(10)]

    updated = update_house_rules(skill_path, runs, updated_on=date(2026, 3, 16))

    assert "W0702" not in updated


def test_update_house_rules_increments_version_and_updates_timestamp(tmp_path: Path) -> None:
    skill_path = tmp_path / "skills/specfact-code-review/SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(_skill_text(version=3, updated_on="2026-03-10"), encoding="utf-8")

    updated = update_house_rules(skill_path, [_run("C901"), _run("C901"), _run("C901")], updated_on=date(2026, 3, 16))

    assert "# House Rules - AI Coding Context (v4)" in updated
    assert "Updated: 2026-03-16 | Module: nold-ai/specfact-code-review" in updated


def test_update_house_rules_enforces_line_cap_by_pruning_lowest_frequency(tmp_path: Path) -> None:
    skill_path = tmp_path / "skills/specfact-code-review/SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(_skill_text(), encoding="utf-8")

    runs = []
    for index, rule in enumerate(("A100", "B200", "C300", "D400", "E500", "F600", "G700"), start=3):
        runs.extend(_run(rule) for _ in range(index))

    updated = update_house_rules(skill_path, runs, updated_on=date(2026, 3, 16))

    assert len(updated.splitlines()) <= MAX_SKILL_LINES
    assert "A100" not in updated
    assert "B200" not in updated
    assert "G700" in updated


def test_update_house_rules_preserves_do_and_dont_sections(tmp_path: Path) -> None:
    skill_path = tmp_path / "skills/specfact-code-review/SKILL.md"
    skill_path.parent.mkdir(parents=True)
    original = _skill_text()
    skill_path.write_text(original, encoding="utf-8")

    updated = update_house_rules(skill_path, [_run("C901"), _run("C901"), _run("C901")], updated_on=date(2026, 3, 16))

    original_do_dont = original.split("## TOP VIOLATIONS", maxsplit=1)[0]
    updated_do_dont = updated.split("## TOP VIOLATIONS", maxsplit=1)[0]
    assert updated_do_dont.replace("(v2)", "(v1)").replace("2026-03-16", "2026-03-10") == original_do_dont


def test_update_house_rules_raises_when_output_exceeds_line_cap(tmp_path: Path) -> None:
    skill_path = tmp_path / "skills/specfact-code-review/SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(
        _skill_text(extra_do_rules=[f"- Extra rule {index}" for index in range(1, 8)]),
        encoding="utf-8",
    )

    try:
        update_house_rules(skill_path, [], updated_on=date(2026, 3, 16))
    except ViolationError as error:
        assert str(MAX_SKILL_LINES) in str(error)
    else:
        raise AssertionError("Expected icontract line-budget assertion to fail")


def test_rules_show_prints_current_skill_content(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    skill_path = tmp_path / SKILL_PATH
    skill_path.parent.mkdir(parents=True)
    content = _skill_text()
    skill_path.write_text(content, encoding="utf-8")

    result = runner.invoke(app, ["review", "rules", "show"])

    assert result.exit_code == 0
    assert result.output == content


def test_rules_show_missing_skill_prints_helpful_error(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["review", "rules", "show"])

    assert result.exit_code == 1
    assert "rules init" in result.output


def test_rules_init_creates_default_skill_without_modifying_claude(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    claude_path = tmp_path / "CLAUDE.md"
    claude_path.write_text("keep me\n", encoding="utf-8")

    result = runner.invoke(app, ["review", "rules", "init"])

    assert result.exit_code == 0
    assert (tmp_path / SKILL_PATH).exists()
    assert claude_path.read_text(encoding="utf-8") == "keep me\n"


def test_rules_init_mirrors_to_cursor_rules(monkeypatch: Any, tmp_path: Path) -> None:
    """Init must copy skill content to .cursor/rules/house_rules.mdc for AI IDE consumption."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["review", "rules", "init"])

    assert result.exit_code == 0
    skill_path = tmp_path / SKILL_PATH
    mirror_path = tmp_path / ".cursor/rules/house_rules.mdc"
    assert skill_path.exists()
    assert mirror_path.exists()
    assert mirror_path.read_text(encoding="utf-8") == skill_path.read_text(encoding="utf-8")


def test_rules_init_creates_cursor_rules_dir_if_missing(monkeypatch: Any, tmp_path: Path) -> None:
    """Init must create .cursor/rules/ when it does not exist."""
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / ".cursor").exists()

    result = runner.invoke(app, ["review", "rules", "init"])

    assert result.exit_code == 0
    assert (tmp_path / ".cursor/rules/house_rules.mdc").exists()


def test_rules_init_mirrors_to_skill_md_ide_locations(monkeypatch: Any, tmp_path: Path) -> None:
    """Init must copy SKILL.md to Claude, Codex, Vibe, GitHub, and Cursor skills locations."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["review", "rules", "init"])

    assert result.exit_code == 0
    content = (tmp_path / SKILL_PATH).read_text(encoding="utf-8")
    for rel_path in IDE_SKILL_PATHS:
        full = tmp_path / rel_path
        assert full.exists(), f"Expected {rel_path} to exist"
        assert full.read_text(encoding="utf-8") == content


def test_rules_update_rederives_top_violations_from_ledger(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    skill_path = tmp_path / SKILL_PATH
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(_skill_text(version=3), encoding="utf-8")

    class FakeLedgerClient:
        def get_recent_runs(self, limit: int = 20) -> list[LedgerRun]:
            assert limit == 20
            return [_run("C901"), _run("C901"), _run("C901"), _run("W0702")]

    monkeypatch.setattr("specfact_code_review.rules.commands.LedgerClient", FakeLedgerClient)

    result = runner.invoke(app, ["review", "rules", "update"])

    assert result.exit_code == 0
    updated = skill_path.read_text(encoding="utf-8")
    assert "# House Rules - AI Coding Context (v4)" in updated
    assert "C901" in updated
    assert (tmp_path / ".cursor/rules/house_rules.mdc").read_text(encoding="utf-8") == updated
    for rel_path in IDE_SKILL_PATHS:
        assert (tmp_path / rel_path).read_text(encoding="utf-8") == updated
