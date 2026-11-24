"""Convert Python test source to OpenAPI examples without executing it."""

from __future__ import annotations

import ast
import tokenize
import warnings
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, TypeGuard

from beartype import beartype
from icontract import ensure, require

from specfact_project.analyzers.python_source import import_aliases, qualified_name


HTTP_METHODS = frozenset({"post", "get", "put", "delete", "patch"})
HTTP_MODULES = frozenset({"requests", "httpx"})
CLIENT_FIXTURES = frozenset({"client", "api_client", "async_client", "http_client", "test_client", "self.client"})
CLIENT_CONSTRUCTORS = frozenset(
    {
        "TestClient",
        "APIClient",
        "fastapi.testclient.TestClient",
        "starlette.testclient.TestClient",
        "rest_framework.test.APIClient",
        "httpx.Client",
        "httpx.AsyncClient",
        "requests.Session",
        "requests.session",
    }
)


def _test_body_nodes(body: Sequence[ast.stmt]) -> Iterator[ast.AST]:
    pending: list[ast.AST] = list(reversed(body))
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield node
        pending.extend(reversed(list(ast.iter_child_nodes(node))))


def _client_assignment(value: ast.AST, aliases: dict[str, str], clients: set[str]) -> bool:
    if isinstance(value, ast.Call):
        constructor = qualified_name(value.func, aliases)
        return constructor in CLIENT_CONSTRUCTORS or constructor.endswith(".test_client")
    return qualified_name(value, {}) in clients


def _test_statements(
    nodes: Sequence[ast.AST],
) -> list[ast.Assign | ast.AnnAssign | ast.Expr | ast.Assert | ast.With | ast.AsyncWith]:
    return sorted(
        (
            node
            for node in nodes
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.Expr, ast.Assert, ast.With, ast.AsyncWith))
        ),
        key=lambda statement: (statement.lineno, statement.col_offset),
    )


def _is_equality_assertion(node: ast.AST) -> TypeGuard[ast.Compare]:
    return isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq)


def _response_attribute(expression: ast.expr) -> ast.Attribute | None:
    attribute = expression.func if isinstance(expression, ast.Call) else expression
    return attribute if isinstance(attribute, ast.Attribute) else None


class OpenAPITestConverter:
    """Extract literal HTTP requests and their asserted responses from Python tests."""

    def __init__(self, repo_path: Path, semgrep_config: Path | None = None) -> None:
        self.repo_path = repo_path.resolve()
        if semgrep_config is not None or (self.repo_path / "tools/semgrep/test-patterns.yml").is_file():
            warnings.warn(
                "Semgrep test-pattern configuration is retired. SpecFact extracts examples from Python test source.",
                UserWarning,
                stacklevel=2,
            )

    @beartype
    @require(lambda self, test_files: isinstance(test_files, list), "Test files must be list")
    @ensure(lambda result: isinstance(result, dict), "Must return dict")
    def extract_examples_from_tests(self, test_files: list[str]) -> dict[str, Any]:
        """Read selected files or file::test references and return examples by operation ID."""
        examples: dict[str, Any] = {}
        for test_ref in test_files:
            path, _, selected_test = test_ref.partition("::")
            test_path = self.repo_path / path
            try:
                with tokenize.open(test_path) as stream:
                    tree = ast.parse(stream.read(), filename=str(test_path))
            except (OSError, SyntaxError, UnicodeError):
                continue
            aliases = import_aliases(tree.body)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
                    continue
                if selected_test and node.name != selected_test:
                    continue
                examples.update(self._extract_examples_from_test_function(node, aliases))
        return examples

    def _extract_examples_from_test_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, module_aliases: dict[str, str]
    ) -> dict[str, dict[str, Any]]:
        """Associate assertions with the request assigned to their response variable."""
        nodes = list(_test_body_nodes(node.body))
        aliases = module_aliases | import_aliases(nodes)
        clients = set(CLIENT_FIXTURES | HTTP_MODULES)
        clients.update(name for name, module in aliases.items() if module in HTTP_MODULES)
        statements = _test_statements(nodes)
        examples: dict[str, Any] = {}
        responses: dict[str, dict[str, Any]] = {}
        for statement in statements:
            if isinstance(statement, ast.Assert):
                inline_example = self._apply_response_assertion(statement, responses, clients)
                if inline_example is not None:
                    examples[inline_example["operation_id"]] = inline_example
                continue
            for value, targets in self._request_bindings(statement):
                for target in targets:
                    responses.pop(target, None)
                example = self._request_example(value, clients)
                self._bind_clients(targets, value, aliases, clients)
                if example is not None:
                    examples[example["operation_id"]] = example
                    responses.update(dict.fromkeys(targets, example))
        return examples

    def _request_bindings(
        self, statement: ast.Assign | ast.AnnAssign | ast.Expr | ast.With | ast.AsyncWith
    ) -> Iterator[tuple[ast.expr | None, list[str]]]:
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            for item in statement.items:
                targets = [item.optional_vars.id] if isinstance(item.optional_vars, ast.Name) else []
                yield item.context_expr, targets
            return
        yield statement.value, self._assignment_names(statement)

    @staticmethod
    def _bind_clients(
        targets: Sequence[str], value: ast.AST | None, aliases: dict[str, str], clients: set[str]
    ) -> None:
        if not targets or value is None:
            return
        if _client_assignment(value, aliases, clients):
            clients.update(targets)
        else:
            clients.difference_update(targets)
        for target in targets:
            aliases.pop(target, None)

    def _request_example(self, value: ast.AST | None, clients: set[str]) -> dict[str, Any] | None:
        if isinstance(value, ast.Await):
            value = value.value
        if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Attribute):
            return None
        method = value.func.attr
        path = self._extract_string_arg(value, 0)
        if method not in HTTP_METHODS or not path or qualified_name(value.func.value, {}) not in clients:
            return None
        operation = f"{method}_{path.replace('/', '_').replace('-', '_').strip('_')}"
        body = self._extract_json_arg(value, "json") or self._extract_json_arg(value, "data") or {}
        return {
            "operation_id": operation,
            "request": {"path": path, "method": method.upper(), "body": body},
        }

    @staticmethod
    def _assignment_names(statement: ast.Assign | ast.AnnAssign | ast.Expr) -> list[str]:
        if isinstance(statement, ast.Assign):
            return [target.id for target in statement.targets if isinstance(target, ast.Name)]
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            return [statement.target.id]
        return []

    def _apply_response_assertion(
        self, statement: ast.Assert, responses: dict[str, dict[str, Any]], clients: set[str]
    ) -> dict[str, Any] | None:
        compare = statement.test
        if not _is_equality_assertion(compare):
            return None
        left = compare.left
        attribute = _response_attribute(left)
        if attribute is None:
            return None
        receiver = attribute.value
        if isinstance(receiver, ast.Name):
            example = responses.get(receiver.id)
            inline = None
        else:
            example = inline = self._request_example(receiver, clients)
        if example is None:
            return None
        self._record_asserted_value(example, attribute.attr, isinstance(left, ast.Call), compare.comparators[0])
        return inline

    def _record_asserted_value(self, example: dict[str, Any], attribute: str, called: bool, value: ast.expr) -> None:
        expected = self._extract_ast_value(value)
        if called:
            if attribute == "json" and expected is not None:
                example["response"] = expected
                example.setdefault("status_code", 200)
        elif attribute == "status_code" and isinstance(expected, int) and not isinstance(expected, bool):
            example["status_code"] = expected

    @beartype
    def _extract_string_arg(self, call: ast.Call, index: int) -> str | None:
        """Return a literal string argument."""
        if index < len(call.args):
            arg = call.args[index]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
        return None

    def _coerce_ast_dict_to_plain(self, value: ast.Dict) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in zip(value.keys, value.values, strict=True):
            if k is None:
                continue
            key = self._extract_ast_value(k)
            val = self._extract_ast_value(v)
            if key is not None:
                result[str(key)] = val
        return result

    @beartype
    def _extract_json_arg(self, call: ast.Call, keyword: str) -> dict[str, Any] | None:
        """Extract JSON/data argument from function call."""
        for keyword_arg in call.keywords:
            if keyword_arg.arg != keyword:
                continue
            inner = keyword_arg.value
            if isinstance(inner, ast.Dict):
                return self._coerce_ast_dict_to_plain(inner)
        return None

    @beartype
    def _extract_ast_value(self, node: ast.AST) -> Any:
        """Extract value from AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Dict):
            return self._coerce_ast_dict_to_plain(node)
        if isinstance(node, ast.List):
            return [self._extract_ast_value(item) for item in node.elts]
        if isinstance(node, ast.Name):
            # Variable reference - can't extract value statically
            return None
        try:
            return ast.unparse(node)
        except (AttributeError, TypeError, ValueError, RecursionError):
            return None
