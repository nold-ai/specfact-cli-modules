from __future__ import annotations

from pathlib import Path

from specfact_code_review.tools.ai_bloat_runner import run_ai_bloat


def _write(tmp_path: Path, source: str) -> Path:
    target = tmp_path / "sample.py"
    target.write_text(source.strip() + "\n", encoding="utf-8")
    return target


def test_unused_optional_param_flags_default_none_without_none_branch(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
from typing import Optional


def greet(name: str, prefix: Optional[str] = None) -> str:
    return f"{name}"
""",
    )

    findings = run_ai_bloat([target])

    assert {finding.rule for finding in findings} == {"ai-bloat.unused-optional-param"}
    assert findings[0].category == "ai_bloat"
    assert findings[0].severity == "info"


def test_optional_param_with_none_branch_is_not_flagged(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
from typing import Optional


def greet(name: str, prefix: Optional[str] = None) -> str:
    if prefix is None:
        return name
    return f"{prefix} {name}"
""",
    )

    assert run_ai_bloat([target]) == []


def test_dead_branch_flags_duplicate_prior_return_guard(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def classify(value: int) -> str:
    if value > 10:
        return "large"
    if value > 10:
        return "still large"
    return "small"
""",
    )

    assert {finding.rule for finding in run_ai_bloat([target])} == {"ai-bloat.dead-branch"}


def test_loc_vs_complexity_flags_long_linear_function(tmp_path: Path) -> None:
    lines = ["def build_values(value: int) -> list[int]:", "    result = []"]
    for index in range(39):
        lines.append(f"    result.append(value + {index})")
    lines.append("    return result")
    target = _write(tmp_path, "\n".join(lines))

    assert {finding.rule for finding in run_ai_bloat([target])} == {"ai-bloat.loc-vs-complexity"}


def test_redundant_intermediate_flags_assign_then_immediate_return(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def total(values: list[int]) -> int:
    result = sum(values)
    return result
""",
    )

    assert {finding.rule for finding in run_ai_bloat([target])} == {"ai-bloat.redundant-intermediate"}


def test_redundant_intermediate_ignores_reused_names(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def total(values: list[int]) -> tuple[int, str]:
    result = sum(values)
    label = f"total={result}"
    return result, label
""",
    )

    assert run_ai_bloat([target]) == []
