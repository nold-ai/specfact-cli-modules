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


def test_duplicate_intent_finding_includes_related_locations_and_intent_key(tmp_path: Path) -> None:
    file_path = tmp_path / "customer_orders.py"
    file_path.write_text(
        """
def normalize_customer_order(order: dict[str, object]) -> dict[str, object]:
    cleaned: dict[str, object] = {}
    for key, value in order.items():
        if value is not None:
            cleaned[key] = str(value).strip()
    return cleaned


def prepare_customer_order(payload: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for name, item in payload.items():
        if item is not None:
            normalized[name] = str(item).strip()
    return normalized
""".strip()
        + "\n",
        encoding="utf-8",
    )

    findings = run_ast_clean_code([file_path])
    duplicate = next(finding for finding in findings if finding.rule == "dry.duplicate-function-shape")

    assert duplicate.intent_key == "customer-order"
    assert duplicate.rewrite_hint
    assert duplicate.related_locations is not None
    assert duplicate.related_locations[0].path == str(file_path)
    assert duplicate.related_locations[0].start_line == 1


def test_duplicate_intent_does_not_group_similar_names_without_matching_shape(tmp_path: Path) -> None:
    file_path = tmp_path / "customer_orders.py"
    file_path.write_text(
        """
def normalize_customer_order(order: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in order.items() if value is not None}


def prepare_customer_order(payload: dict[str, object]) -> list[str]:
    return [str(item) for item in payload.values()]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    findings = run_ast_clean_code([file_path])

    assert not any(finding.rule == "dry.duplicate-function-shape" for finding in findings)


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


def test_run_ast_clean_code_reports_mixed_dependency_roles_for_injected_dependencies(tmp_path: Path) -> None:
    file_path = tmp_path / "target.py"
    file_path.write_text(
        """
class SyncClient:
    def sync(self) -> None:
        self.repository.load()
        self.http_client.post()
""".strip()
        + "\n",
        encoding="utf-8",
    )

    findings = run_ast_clean_code([file_path])

    assert any(finding.category == "solid" and finding.rule == "solid.mixed-dependency-role" for finding in findings)


def test_run_ast_clean_code_continues_after_parse_error(tmp_path: Path) -> None:
    broken_path = tmp_path / "broken.py"
    broken_path.write_text("def broken(:\n    pass\n", encoding="utf-8")
    healthy_path = tmp_path / "healthy.py"
    healthy_path.write_text(
        """
def _unused_helper(value: int) -> int:
    return value + 1
""".strip()
        + "\n",
        encoding="utf-8",
    )

    findings = run_ast_clean_code([broken_path, healthy_path])

    assert any(finding.category == "tool_error" and finding.file == str(broken_path) for finding in findings)
    assert any(finding.rule == "yagni.unused-private-helper" for finding in findings)


def test_run_ast_clean_code_returns_tool_error_for_syntax_error(tmp_path: Path) -> None:
    file_path = tmp_path / "broken.py"
    file_path.write_text("def broken(:\n    pass\n", encoding="utf-8")

    findings = run_ast_clean_code([file_path])

    assert len(findings) == 1
    assert findings[0].category == "tool_error"
    assert findings[0].tool == "ast"
