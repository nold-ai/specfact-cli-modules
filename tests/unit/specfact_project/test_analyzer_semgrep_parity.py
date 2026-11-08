from pathlib import Path
from typing import Any

import pytest
from specfact_cli.models.plan import Feature

from specfact_project.analyzers.code_analyzer import CodeAnalyzer, _SemgrepClassScope


@pytest.fixture
def analyzer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CodeAnalyzer:
    monkeypatch.setenv("TEST_MODE", "true")
    return CodeAnalyzer(tmp_path)


def enhance(
    analyzer: CodeAnalyzer,
    feature: Feature,
    findings: list[dict[str, Any]],
    start: int | None = 10,
    end: int | None = 20,
) -> None:
    analyzer._enhance_feature_with_semgrep(
        feature, findings, _SemgrepClassScope(analyzer.repo_path / "sample.py", "Service", start, end)
    )


def finding(rule: str, **kwargs: Any) -> dict[str, Any]:
    return {"check_id": rule, "message": "Service", "path": "", **kwargs}


@pytest.mark.parametrize(
    ("rule", "expected"),
    [
        ("route-detection-auth", "has_api_endpoints"),
        ("api-endpoint-security", "has_api_endpoints"),
        ("model-detection-crud", "has_database_models"),
        ("database-model-auth", "has_database_models"),
        ("crud-auth", "has_crud_operations"),
        ("permission-framework", "has_auth_patterns"),
        ("async-test", "has_framework_patterns"),
        ("pytest-antipattern", "has_test_patterns"),
        ("deprecated-security", "has_anti_patterns"),
        ("command-injection", "has_security_issues"),
    ],
)
def test_evidence_priority_is_distinct_from_enhancement(analyzer: CodeAnalyzer, rule: str, expected: str) -> None:
    result = analyzer._extract_semgrep_evidence([finding(rule, path="unrelated.py")], "Service", 10, 20)
    assert [name for name, value in result.items() if value] == [expected]


@pytest.mark.parametrize("bad_line", ["15", [15]])
def test_evidence_keeps_raw_line_errors_and_class_short_circuit(analyzer: CodeAnalyzer, bad_line: Any) -> None:
    with pytest.raises(TypeError):
        analyzer._extract_semgrep_evidence(
            [finding("auth", message="other", start={"line": bad_line})], "Service", 10, 20
        )
    assert analyzer._extract_semgrep_evidence([finding("auth", start={"line": bad_line})], "Service", 10, 20)[
        "has_auth_patterns"
    ]


def test_enhancement_keeps_outcome_category_order_and_first_three_constraints(analyzer: CodeAnalyzer) -> None:
    feature = Feature.model_validate({"key": "FEATURE-1", "title": "Service", "outcomes": ["existing"]})
    findings = [
        finding("crud-auth", extra={"metadata": {"permission": "admin"}}),
        finding("crud", extra={"metadata": {"operation": "create"}, "message": "create_user"}),
        finding("model-detection", extra={"metadata": {"model": "User"}}),
        finding("route-detection", extra={"metadata": {"method": "get", "path": "/one"}}),
        finding("route-detection", extra={"metadata": {"method": "post", "path": "/two"}}),
        *[finding("antipattern", message=f"Service quality {n}") for n in range(4)],
        *[finding("security", message=f"Service issue {n}") for n in range(4)],
    ]
    enhance(analyzer, feature, findings)
    assert feature.outcomes == [
        "existing",
        "Exposes API endpoints: GET /one, POST /two",
        "Defines data models: User",
        "Requires authentication: admin",
        "Provides CRUD operations: CREATE user",
    ]
    assert feature.constraints == [
        "Code quality: Service quality 0; Service quality 1; Service quality 2",
        "Issues detected: Service issue 0; Service issue 1; Service issue 2",
    ]
    assert analyzer.themes == {"API", "Database", "Security"}


@pytest.mark.parametrize(
    ("start", "end", "line", "expected"),
    [(10, None, 1000, True), (10, 20, 25, False), (10, 20, 15, True), (None, None, 15, False)],
)
def test_enhancement_keeps_unbounded_anti_pattern_and_bounded_no_fallback(
    analyzer: CodeAnalyzer, start: int | None, end: int | None, line: int, expected: bool
) -> None:
    feature = Feature.model_validate({"key": "FEATURE-1", "title": "Service"})
    enhance(analyzer, feature, [finding("antipattern", message="quality", start={"line": line})], start, end)
    assert feature.constraints == (["Code quality: quality"] if expected else [])


@pytest.mark.parametrize(
    ("rule", "extra", "message", "expected"),
    [
        ("route-detection-auth", {}, "Service", []),
        ("api-endpoint", {"metadata": {"method": "get", "path": "/one"}}, "Service", []),
        ("crud", {"message": "single"}, "Service create_user", []),
        ("crud", {}, "Service get_user create_", []),
        ("crud", {"message": "create_user_name"}, "Service", ["Provides CRUD operations: UNKNOWN user_name"]),
        ("crud", {"metadata": {"operation": "get"}}, "Service", ["Provides CRUD operations: GET unknown"]),
    ],
)
def test_enhancement_keeps_branch_selection_and_crud_fallback_rules(
    analyzer: CodeAnalyzer, rule: str, extra: dict[str, Any], message: str, expected: list[str]
) -> None:
    feature = Feature.model_validate({"key": "FEATURE-1", "title": "Service"})
    enhance(analyzer, feature, [finding(rule, extra=extra, message=message)])
    assert feature.outcomes == expected


def test_enhancement_keeps_path_filter_and_partial_theme_before_failure(analyzer: CodeAnalyzer) -> None:
    feature = Feature.model_validate({"key": "FEATURE-1", "title": "Service", "outcomes": ["existing"]})
    enhance(analyzer, feature, [finding("auth", path="unrelated.py")])
    assert analyzer.themes == set()
    with pytest.raises(AttributeError):
        enhance(
            analyzer,
            feature,
            [
                finding("route-detection", extra={"metadata": {"method": "get", "path": "/one"}}),
                finding("route-detection", extra={"metadata": None}),
            ],
        )
    assert analyzer.themes == {"API"}
    assert feature.outcomes == ["existing"]


def test_enhancement_keeps_raw_line_comparison_failure(analyzer: CodeAnalyzer) -> None:
    feature = Feature.model_validate({"key": "FEATURE-1", "title": "Service"})
    with pytest.raises(TypeError):
        enhance(analyzer, feature, [finding("auth", message="other", start={"line": "15"})])
