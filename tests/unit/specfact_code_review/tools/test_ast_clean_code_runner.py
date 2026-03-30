from __future__ import annotations

from pathlib import Path

from specfact_code_review.tools.ast_clean_code_runner import run_ast_clean_code


def test_run_ast_clean_code_reports_unused_private_helper(tmp_path: Path) -> None:
    file_path = tmp_path / "target.py"
    file_path.write_text(
        """
def _unused_helper(value: int) -> int:
    return value + 1


def public_api(value: int) -> int:
    return value * 2
""".strip()
        + "\n",
        encoding="utf-8",
    )

    findings = run_ast_clean_code([file_path])

    assert any(finding.category == "yagni" and finding.rule == "yagni.unused-private-helper" for finding in findings)


def test_run_ast_clean_code_reports_duplicate_function_shapes(tmp_path: Path) -> None:
    file_path = tmp_path / "target.py"
    file_path.write_text(
        """
def first(items: list[int]) -> list[int]:
    cleaned: list[int] = []
    for item in items:
        if item > 0:
            cleaned.append(item * 2)
    return cleaned


def second(values: list[int]) -> list[int]:
    doubled: list[int] = []
    for value in values:
        if value > 0:
            doubled.append(value * 2)
    return doubled
""".strip()
        + "\n",
        encoding="utf-8",
    )

    findings = run_ast_clean_code([file_path])

    assert any(finding.category == "dry" and finding.rule == "dry.duplicate-function-shape" for finding in findings)


def test_run_ast_clean_code_reports_mixed_dependency_roles(tmp_path: Path) -> None:
    file_path = tmp_path / "target.py"
    file_path.write_text(
        """
def sync_customer(customer_id: str) -> None:
    repository.load(customer_id)
    http_client.post("/customers/sync", json={"customer_id": customer_id})
""".strip()
        + "\n",
        encoding="utf-8",
    )

    findings = run_ast_clean_code([file_path])

    assert any(finding.category == "solid" and finding.rule == "solid.mixed-dependency-role" for finding in findings)


def test_run_ast_clean_code_returns_tool_error_for_syntax_error(tmp_path: Path) -> None:
    file_path = tmp_path / "broken.py"
    file_path.write_text("def broken(:\n    pass\n", encoding="utf-8")

    findings = run_ast_clean_code([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "ast"
