from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT = REPO_ROOT / "packages/specfact-project/resources/prompts/specfact.08-simplify.md"
SKILL = (
    REPO_ROOT / "packages/specfact-code-review/src/specfact_code_review/resources/skills/specfact-code-review/SKILL.md"
)


def test_simplify_prompt_guides_interactive_walkthrough_levels() -> None:
    text = PROMPT.read_text(encoding="utf-8")

    assert "vibe coder" in text
    assert "junior developer" in text
    assert "senior/pro" in text
    assert "headless agent" in text
    assert "safe_mechanical" in text
    assert "needs_tests" in text
    assert "design_judgment" in text
    assert "preserve" in text
    assert "recommended, applied, kept, skipped, failed" in text
    assert "this report is the evidence file" in text
    assert "| file | line | rule | guidance_kind | recommended_action | action_status | evidence |" in text


def test_code_review_skill_teaches_llms_how_to_apply_simplification_guidance() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "Ask for walkthrough level" in text
    assert "safe_mechanical" in text
    assert "needs_tests" in text
    assert "design_judgment" in text
    assert "preserve" in text
    assert "recommended, applied, kept, skipped, failed" in text
    assert "In headless mode, process one file at a time" in text
    assert "file, line, rule, guidance_kind, recommended_action, action_status, evidence" in text
