from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT = REPO_ROOT / "packages/specfact-project/resources/prompts/specfact.08-simplify.md"
SKILL = (
    REPO_ROOT / "packages/specfact-code-review/src/specfact_code_review/resources/skills/specfact-code-review/SKILL.md"
)
SKILL_COPIES = (
    SKILL,
    REPO_ROOT / "skills/specfact-code-review/SKILL.md",
    REPO_ROOT / ".vibe/skills/specfact-code-review/SKILL.md",
)


def _assert_contains_all(text: str, required: tuple[str, ...]) -> None:
    missing = [item for item in required if item not in text]

    assert missing == []


def test_simplify_prompt_guides_interactive_walkthrough_levels() -> None:
    text = PROMPT.read_text(encoding="utf-8")

    _assert_contains_all(
        text,
        (
            "vibe coder",
            "junior developer",
            "senior/pro",
            "headless agent",
            "safe_mechanical",
            "needs_tests",
            "design_judgment",
            "preserve",
            "recommended, applied, kept, skipped, failed",
            "this report is the evidence file",
            "decision card",
            "Why it might need to stay",
            "Proposed patch preview",
            "Validation plan",
            "unknown intent defaults to keep or skip",
            "API, callback signature, framework hook, adapter seam, public symbol",
            "| file | line | rule | guidance_kind | recommended_action | action_status | evidence |",
        ),
    )


def test_code_review_skill_teaches_llms_how_to_apply_simplification_guidance() -> None:
    for skill_path in SKILL_COPIES:
        text = skill_path.read_text(encoding="utf-8")

        _assert_contains_all(
            text,
            (
                "Ask for walkthrough level",
                "safe_mechanical",
                "needs_tests",
                "design_judgment",
                "preserve",
                "recommended, applied, kept, skipped, failed",
                "In headless mode, process one file at a time",
                "file, line, rule, guidance_kind, recommended_action, action_status, evidence",
                "remove AI bloat",
                "apply clean code",
                "interactive cleanup coach",
                "decision card",
                "exact patch preview",
                "API, callback, framework hook, adapter, public symbol",
                "default to keep or skip",
                "Run targeted tests or rerun simplify review after each accepted file",
                "Don't ask non-expert users to infer code intent from a raw warning",
            ),
        )
