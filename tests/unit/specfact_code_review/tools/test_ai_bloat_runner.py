from __future__ import annotations

from pathlib import Path

import pytest

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
    assert findings[0].guidance_kind == "design_judgment"
    assert findings[0].recommended_action == "make_required"


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


def test_dead_branch_ignores_duplicate_guard_after_else_path(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def classify(value: int) -> str:
    if value > 10:
        return "large"
    else:
        value += 1
    if value > 10:
        return "now large"
    return "small"
""",
    )

    assert run_ai_bloat([target]) == []


def test_dead_branch_ignores_nonterminal_duplicate_guard(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def classify(value: int) -> str:
    label = "small"
    if value > 10:
        return "large"
    if value > 10:
        label = "still large"
    return label
""",
    )

    assert run_ai_bloat([target]) == []


def test_dead_branch_ignores_duplicate_guard_with_else(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def classify(value: int) -> str:
    if value > 10:
        return "large"
    if value > 10:
        return "still large"
    else:
        return "fallback"
    return "small"
""",
    )

    assert run_ai_bloat([target]) == []


def test_dead_branch_ignores_duplicate_guard_after_assignment(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def classify(value: int) -> str:
    if value > 10:
        return "large"
    value = 12
    if value > 10:
        return "now large"
    return "small"
""",
    )

    assert run_ai_bloat([target]) == []


def test_dead_branch_ignores_impure_duplicate_guard(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def classify(value: object) -> str:
    if value.ready():
        return "ready"
    if value.ready():
        return "still ready"
    return "not ready"
""",
    )

    assert run_ai_bloat([target]) == []


def test_loc_vs_complexity_flags_long_linear_function(tmp_path: Path) -> None:
    lines = ["def build_values(value: int) -> list[int]:", "    result = []"]
    for index in range(39):
        lines.append(f"    result.append(value + {index})")
    lines.append("    return result")
    target = _write(tmp_path, "\n".join(lines))

    findings = run_ai_bloat([target])

    assert {finding.rule for finding in findings} == {"ai-bloat.loc-vs-complexity"}
    assert findings[0].guidance_kind == "design_judgment"
    assert findings[0].recommended_action == "inspect"


def test_redundant_intermediate_flags_assign_then_immediate_return(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def total(values: list[int]) -> int:
    result = sum(values)
    return result
""",
    )

    findings = run_ai_bloat([target])

    assert {finding.rule for finding in findings} == {"ai-bloat.redundant-intermediate"}
    assert findings[0].guidance_kind == "safe_mechanical"
    assert findings[0].recommended_action == "inline"
    assert findings[0].fixable is True


@pytest.mark.parametrize(
    ("source", "expected_rule", "expected_pattern"),
    [
        (
            """
def normalize_names(names: list[str]) -> list[str]:
    result: list[str] = []
    for name in names:
        result.append(name.strip().lower())
    return result
""",
            "ai-bloat.manual-accumulator-loop",
            "manual-accumulator-loop",
        ),
        (
            """
def is_allowed(role: str) -> bool:
    if role in {"admin", "owner"}:
        return True
    return False
""",
            "ai-bloat.verbose-bool-return",
            "verbose-bool-return",
        ),
        (
            """
def normalized_name(name: str | None) -> str | None:
    if name is None:
        return None
    return name.strip()
""",
            "ai-bloat.redundant-none-branch",
            "redundant-none-branch",
        ),
        (
            """
def load_customer(customer_id: str) -> dict[str, str]:
    return fetch_customer(customer_id)


def read_customer(customer_id: str) -> dict[str, str]:
    return load_customer(customer_id)
""",
            "ai-bloat.wrapper-chain",
            "wrapper-chain",
        ),
        (
            """
def parse_customer(raw: str) -> dict[str, str]:
    try:
        return parse_json(raw)
    except Exception:
        raise
""",
            "ai-bloat.pass-through-try-except",
            "pass-through-try-except",
        ),
        (
            """
def status_label(code: str) -> str:
    if code == "new":
        return "New"
    if code == "done":
        return "Done"
    if code == "blocked":
        return "Blocked"
    return "Unknown"
""",
            "ai-bloat.table-lookup-candidate",
            "table-lookup-candidate",
        ),
        (
            """
def highest_score(scores: list[int]) -> int | None:
    best = None
    for score in scores:
        if best is None or score > best:
            best = score
    return best
""",
            "ai-bloat.stdlib-replacement-candidate",
            "stdlib-replacement-candidate",
        ),
    ],
)
def test_expanded_simplification_patterns_emit_metadata(
    tmp_path: Path,
    source: str,
    expected_rule: str,
    expected_pattern: str,
) -> None:
    target = _write(tmp_path, source)

    findings = run_ai_bloat([target])

    matching = [finding for finding in findings if finding.rule == expected_rule]
    assert len(matching) == 1
    assert matching[0].category == "ai_bloat"
    assert matching[0].severity == "info"
    assert matching[0].confidence == "high"
    assert matching[0].canonical_pattern == expected_pattern
    assert matching[0].rewrite_hint
    assert matching[0].estimated_deletion_lines is not None
    assert matching[0].guidance_kind in {"safe_mechanical", "needs_tests", "design_judgment", "preserve"}
    assert matching[0].recommended_action is not None
    assert matching[0].clean_code_principle is not None
    assert matching[0].rationale
    assert matching[0].safety_checks


def test_abstract_optional_param_is_preserve_guidance(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
from abc import ABC, abstractmethod


class Provider(ABC):
    @abstractmethod
    def fetch(self, key: str, timeout: int | None = None) -> str:
        raise NotImplementedError
""",
    )

    findings = run_ai_bloat([target])

    assert {finding.rule for finding in findings} == {"ai-bloat.unused-optional-param"}
    assert findings[0].guidance_kind == "preserve"
    assert findings[0].recommended_action == "keep"
    assert findings[0].preserve_reason == "abstract method signature can be an implementation contract"


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


def test_simplification_patterns_ignore_ambiguous_domain_logic(tmp_path: Path) -> None:
    target = _write(
        tmp_path,
        """
def classify_score(score: int) -> str:
    if score > 90:
        return "excellent"
    if score > 70:
        return "good"
    if score > 50:
        return "review"
    return "blocked"
""",
    )

    assert run_ai_bloat([target]) == []
