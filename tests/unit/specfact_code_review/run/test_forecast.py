from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

from specfact_code_review.run.findings import ReviewFinding
from specfact_code_review.run.forecast import build_cleanup_forecast


def _finding(*, guidance_kind: str, deletion_lines: int) -> ReviewFinding:
    return ReviewFinding(
        category="ai_bloat",
        severity="info",
        tool="ast",
        rule="ai-bloat.redundant-intermediate",
        file="src/example.py",
        line=1,
        message="Simplify local code.",
        confidence="high",
        rewrite_hint="Inline the temporary.",
        canonical_pattern="one-use-temporary",
        estimated_deletion_lines=deletion_lines,
        guidance_kind=cast(
            Literal["safe_mechanical", "needs_tests", "design_judgment", "preserve"],
            guidance_kind,
        ),
        recommended_action="keep" if guidance_kind == "preserve" else "inline",
        clean_code_principle="api_stability" if guidance_kind == "preserve" else "kiss",
        rationale="The local variable is assigned once and returned.",
        safety_checks=["same expression is returned"],
        preserve_reason="Public compatibility boundary." if guidance_kind == "preserve" else None,
        action_status="recommended",
    )


def test_build_cleanup_forecast_counts_loc_and_weighted_bloat(tmp_path: Path) -> None:
    source = tmp_path / "src" / "example.py"
    source.parent.mkdir()
    source.write_text("# comment\n\nvalue = 1\nprint(value)\n", encoding="utf-8")
    test_file = tmp_path / "tests" / "test_example.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_example():\n    assert True\n", encoding="utf-8")

    forecast = build_cleanup_forecast(
        [
            _finding(guidance_kind="safe_mechanical", deletion_lines=2),
            _finding(guidance_kind="preserve", deletion_lines=5),
        ],
        [source, test_file],
    )

    assert forecast.reviewed_loc.production == 2
    assert forecast.reviewed_loc.tests == 2
    assert forecast.estimated_deletion_lines.low == 2
    assert forecast.estimated_deletion_lines.high == 2
    assert forecast.by_guidance_kind["preserve"].estimated_deletion_lines == 5
    assert forecast.ai_bloat_index.weighted_bloat_points_per_kloc == 250.0


def test_build_cleanup_forecast_skips_undecodable_python_files(tmp_path: Path) -> None:
    source = tmp_path / "legacy.py"
    source.write_bytes(b"\xff\xfe\x00")

    forecast = build_cleanup_forecast([_finding(guidance_kind="safe_mechanical", deletion_lines=2)], [source])

    assert forecast.reviewed_loc.total == 0
    assert forecast.estimated_deletion_lines.expected == 2
