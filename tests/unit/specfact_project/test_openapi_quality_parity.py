import ast
from pathlib import Path
from typing import Any

import pytest

from specfact_project.generators.test_to_openapi import OpenAPITestConverter


def test_failed_ast_unparsing_preserves_none_fallbacks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_MODE", "true")
    converter = OpenAPITestConverter(tmp_path)
    call = ast.parse("client.get(prefix + suffix)", mode="eval").body
    assert isinstance(call, ast.Call)

    def unavailable(_node: ast.AST) -> str:
        raise RuntimeError("unparse unavailable")

    monkeypatch.setattr(ast, "unparse", unavailable)

    assert converter._extract_string_arg(call, 0) is None
    assert converter._extract_ast_value(call.args[0]) is None


@pytest.mark.parametrize(
    ("response", "expected_response"),
    [("response.json()", {}), ("client.response.json()", {"response": {"id": 1}, "status_code": 200})],
)
def test_public_ast_examples_preserve_request_and_response_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, response: str, expected_response: dict[str, Any]
) -> None:
    monkeypatch.setenv("TEST_MODE", "true")
    (tmp_path / "test_api.py").write_text(
        "def test_create():\n"
        "    response = client.post('/api/users', json={'name': '雪', 'active': True, 'tags': [1, None]})\n"
        f"    assert {response} == {{'id': 1}}\n"
        "def test_other():\n    client.get('/other')\n",
        encoding="utf-8",
    )

    result = OpenAPITestConverter(tmp_path).extract_examples_from_tests(["test_api.py::test_create"])

    assert result == {
        "post_api_users": {
            "operation_id": "post_api_users",
            "request": {
                "path": "/api/users",
                "method": "POST",
                "body": {"name": "雪", "active": True, "tags": [1, None]},
            },
            **expected_response,
        }
    }


def test_invalid_and_missing_test_files_produce_no_examples(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_MODE", "true")
    (tmp_path / "test_bad.py").write_text("def test_bad(:\n", encoding="utf-8")

    assert OpenAPITestConverter(tmp_path).extract_examples_from_tests(["missing.py", "test_bad.py"]) == {}


def test_empty_native_results_keep_exact_ast_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_MODE", raising=False)
    config = tmp_path / "rules.yml"
    config.write_text("rules: []\n", encoding="utf-8")
    (tmp_path / "test_api.py").write_text("def test_get():\n    client.get('/users')\n", encoding="utf-8")
    converter = OpenAPITestConverter(tmp_path, semgrep_config=config)
    monkeypatch.setattr(converter, "_run_semgrep", lambda _path: [])

    assert converter.extract_examples_from_tests(["test_api.py"]) == {
        "get_users": {"operation_id": "get_users", "request": {"path": "/users", "method": "GET", "body": {}}}
    }


def test_native_interruption_is_not_converted_to_empty_examples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TEST_MODE", raising=False)
    config = tmp_path / "rules.yml"
    config.write_text("rules: []\n", encoding="utf-8")
    (tmp_path / "test_api.py").write_text("def test_get():\n    client.get('/users')\n", encoding="utf-8")
    converter = OpenAPITestConverter(tmp_path, semgrep_config=config)

    def interrupt(_path: Path) -> list[dict[str, Any]]:
        raise KeyboardInterrupt

    monkeypatch.setattr(converter, "_run_semgrep", interrupt)

    with pytest.raises(KeyboardInterrupt):
        converter.extract_examples_from_tests(["test_api.py"])


@pytest.mark.parametrize("both_rules", [False, True])
@pytest.mark.parametrize(
    ("argument", "expected_path", "expected_body"),
    [("variable, ", "variable", {"ignored": 1}), ("", "/users-list", {"name": "雪"})],
)
def test_native_examples_keep_rule_precedence_and_function_request_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    both_rules: bool,
    argument: str,
    expected_path: str,
    expected_body: dict[str, Any],
) -> None:
    monkeypatch.setenv("TEST_MODE", "true")
    path = tmp_path / "test_api.py"
    path.write_text(
        "def test_create():\n"
        f"    client.post({argument}json={{'ignored': 1}})\n"
        "    client.post('/users-list', json={}, data={'name': '雪'})\n"
        "    client.get('/later')\n",
        encoding="utf-8",
    )
    rule = "extract-test-request-data" + ("-extract-test-response-data" if both_rules else "")
    converter = OpenAPITestConverter(tmp_path)
    result = converter._parse_semgrep_results([{"check_id": rule, "start": {"line": 3}}], path)
    operation = "post_" + expected_path.replace("/", "_").replace("-", "_").strip("_")
    assert result == {operation: {"request": {"path": expected_path, "method": "POST", "body": expected_body}}}


def test_native_example_merge_keeps_latest_request_and_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_MODE", "true")
    path = tmp_path / "test_api.py"
    path.write_text("def test_api(): pass", encoding="utf-8")
    converter = OpenAPITestConverter(tmp_path)
    monkeypatch.setattr(
        converter, "_extract_request_example", lambda _, line: {"operation_id": "operation", "request": {"line": line}}
    )
    monkeypatch.setattr(
        converter,
        "_extract_response_example",
        lambda _, line: {"operation_id": "operation", "response": {"line": line}, "status_code": 201},
    )
    results = [
        {"check_id": rule, "start": {"line": line}}
        for rule, line in [
            ("extract-test-response-data", 1),
            ("extract-test-request-data", 2),
            ("unknown", 3),
            ("extract-test-request-data", 4),
        ]
    ]
    assert converter._parse_semgrep_results(results, path) == {
        "operation": {"response": {"line": 1}, "status_code": 201, "request": {"line": 4}}
    }


def test_native_example_missing_match_and_invalid_file_are_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_MODE", "true")
    converter = OpenAPITestConverter(tmp_path)
    path = tmp_path / "test_api.py"
    path.write_text("def test_api(): pass", encoding="utf-8")
    assert (
        converter._parse_semgrep_results([{"check_id": "extract-test-request-data", "start": {"line": 99}}], path) == {}
    )
    path.write_text("invalid (", encoding="utf-8")
    assert converter._parse_semgrep_results([{"check_id": "extract-test-request-data"}], path) == {}


@pytest.mark.parametrize("failure", ["done", "cancel"])
def test_native_cancellation_error_preserves_nonwaiting_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from concurrent.futures import Future
    from types import SimpleNamespace

    import specfact_project.generators.test_to_openapi as module

    monkeypatch.delenv("TEST_MODE", raising=False)
    config = tmp_path / "rules.yml"
    config.write_text("rules: []\n", encoding="utf-8")
    (tmp_path / "test_api.py").write_text("def test_get(): pass", encoding="utf-8")
    shutdowns: list[dict[str, bool]] = []

    def done() -> bool:
        if failure == "done":
            raise ValueError("done")
        return False

    future: Future[list[dict[str, Any]]] = Future()
    future.set_exception(KeyboardInterrupt())
    monkeypatch.setattr(future, "done", done)
    monkeypatch.setattr(future, "cancel", lambda: (_ for _ in ()).throw(ValueError("cancel")))
    executor = SimpleNamespace(submit=lambda *_: future, shutdown=lambda **kwargs: shutdowns.append(kwargs))
    monkeypatch.setattr(module, "ThreadPoolExecutor", lambda **_: executor)
    monkeypatch.setattr(module, "as_completed", lambda futures: list(futures))
    with pytest.raises(ValueError, match=failure):
        OpenAPITestConverter(tmp_path, semgrep_config=config).extract_examples_from_tests(["test_api.py"])
    assert shutdowns == [{"wait": False}]


def test_later_function_failure_retains_preceding_examples(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_MODE", "true")
    (tmp_path / "test_api.py").write_text("def test_first(): pass\ndef test_second(): pass", encoding="utf-8")
    converter = OpenAPITestConverter(tmp_path)

    def extract(node: Any) -> dict[str, Any]:
        if node.name == "test_second":
            raise RuntimeError("later function")
        return {"operation_id": "get_users", "request": {"path": "/users"}}

    monkeypatch.setattr(converter, "_extract_examples_from_test_function", extract)
    assert converter.extract_examples_from_tests(["test_api.py"]) == {
        "get_users": {"operation_id": "get_users", "request": {"path": "/users"}}
    }
