"""
FastAPI framework extractor for sidecar validation.

This module extracts routes and schemas from FastAPI applications.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from beartype import beartype
from icontract import ensure, require

from specfact_codebase.validators.sidecar.frameworks.base import BaseFrameworkExtractor, RouteInfo


_ROUTE_HTTP_METHODS = frozenset(
    {"get", "post", "put", "delete", "patch", "options", "head", "trace"},
)
_FASTAPI_EXTRA_EXCLUDED_DIR_NAMES = frozenset({".mypy_cache", ".pytest_cache", ".ruff_cache"})


def _content_suggests_fastapi(content: str) -> bool:
    return "from fastapi import" in content or "FastAPI(" in content


def _read_text_if_exists(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return None


class FastAPIExtractor(BaseFrameworkExtractor):
    """FastAPI framework extractor."""

    @beartype
    def _path_touches_excluded_dir(self, path: Path) -> bool:
        return super()._path_touches_excluded_dir(path) or any(
            part in _FASTAPI_EXTRA_EXCLUDED_DIR_NAMES for part in path.parts
        )

    @beartype
    @require(lambda repo_path: repo_path.exists(), "Repository path must exist")
    @require(lambda repo_path: repo_path.is_dir(), "Repository path must be a directory")
    @ensure(lambda result: isinstance(result, bool), "Must return bool")
    def detect(self, repo_path: Path) -> bool:
        """
        Detect if this framework is used in the repository.

        Args:
            repo_path: Path to repository root

        Returns:
            True if this framework is detected
        """
        for candidate_file in ["main.py", "app.py"]:
            file_path = repo_path / candidate_file
            if not file_path.exists():
                continue
            if self._path_touches_excluded_dir(file_path):
                continue
            content = _read_text_if_exists(file_path)
            if content is not None and _content_suggests_fastapi(content):
                return True

        for search_path in [repo_path, repo_path / "src", repo_path / "app", repo_path / "backend" / "app"]:
            if search_path.exists() and self._scan_known_app_files(search_path):
                return True

        return False

    @beartype
    def _scan_known_app_files(self, search_path: Path) -> bool:
        for py_file in self._iter_python_files(search_path):
            if py_file.name not in {"main.py", "app.py"}:
                continue
            content = _read_text_if_exists(py_file)
            if content is not None and _content_suggests_fastapi(content):
                return True
        return False

    @beartype
    @require(lambda repo_path: repo_path.exists(), "Repository path must exist")
    @require(lambda repo_path: repo_path.is_dir(), "Repository path must be a directory")
    @ensure(lambda result: isinstance(result, list), "Must return list")
    def extract_routes(self, repo_path: Path) -> list[RouteInfo]:
        """
        Extract route information from framework-specific patterns.

        Args:
            repo_path: Path to repository root

        Returns:
            List of RouteInfo objects with extracted routes
        """
        results: list[RouteInfo] = []

        for search_path in [repo_path, repo_path / "src", repo_path / "app", repo_path / "backend" / "app"]:
            if not search_path.exists():
                continue
            for py_file in self._iter_python_files(search_path):
                try:
                    routes = self._extract_routes_from_file(py_file)
                    results.extend(routes)
                except (SyntaxError, UnicodeDecodeError, PermissionError):
                    continue

        return results

    @beartype
    @require(lambda repo_path: repo_path.exists(), "Repository path must exist")
    @require(lambda routes: isinstance(routes, list), "Routes must be a list")
    @ensure(lambda result: isinstance(result, dict), "Must return dict")
    def extract_schemas(self, repo_path: Path, routes: list[RouteInfo]) -> dict[str, dict[str, Any]]:
        """
        Extract request/response schemas from framework-specific patterns.

        Args:
            repo_path: Path to repository root (reserved for future schema mining)
            routes: List of extracted routes (reserved for future schema mining)

        Returns:
            Dictionary mapping route identifiers to schema dictionaries
        """
        _ = (repo_path, routes)
        # Placeholder until Pydantic schema mining is implemented.
        return {}

    @beartype
    def _extract_routes_from_file(self, py_file: Path) -> list[RouteInfo]:
        """Extract routes from a Python file."""
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError, PermissionError):
            return []

        results: list[RouteInfo] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                results.extend(self._extract_routes_from_function(node))

        return results

    @beartype
    def _path_method_from_route_call(self, decorator: ast.Call) -> tuple[str, str] | None:
        """If ``decorator`` is ``@app.get`` / ``@router.post`` / …, return ``(METHOD, path)``."""
        if isinstance(decorator.func, ast.Attribute):
            attr = decorator.func.attr.lower()
            if attr not in _ROUTE_HTTP_METHODS:
                return None
            path = "/"
            if decorator.args:
                path_arg = self._extract_string_literal(decorator.args[0])
                if path_arg:
                    path = path_arg
            return attr.upper(), path
        if isinstance(decorator.func, ast.Name):
            name = decorator.func.id.lower()
            if name not in _ROUTE_HTTP_METHODS:
                return None
            path = "/"
            if decorator.args:
                path_arg = self._extract_string_literal(decorator.args[0])
                if path_arg:
                    path = path_arg
            return name.upper(), path
        return None

    @beartype
    def _path_methods_from_api_route_call(self, decorator: ast.Call) -> list[tuple[str, str]]:
        """If ``decorator`` is ``@router.api_route(path, methods=[...])``, return all methods + path."""
        if not isinstance(decorator.func, ast.Attribute):
            return []
        if decorator.func.attr != "api_route":
            return []
        path = "/"
        if decorator.args:
            path_arg = self._extract_string_literal(decorator.args[0])
            if path_arg:
                path = path_arg
        methods: list[str] = []
        for kw in decorator.keywords:
            if kw.arg != "methods":
                continue
            if isinstance(kw.value, (ast.List, ast.Tuple)):
                for elt in kw.value.elts:
                    lit = self._extract_string_literal(elt)
                    if lit:
                        methods.append(lit.strip().upper())
        if not methods:
            return [("GET", path)]
        return [(method, path) for method in methods]

    @beartype
    def _extract_routes_from_function(self, func_node: ast.FunctionDef) -> list[RouteInfo]:
        """Extract route information from a function with FastAPI decorators."""
        matched_routes: list[tuple[str, str]] = []

        for decorator in func_node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            got = self._path_method_from_route_call(decorator)
            if got is not None:
                matched_routes.append(got)
                continue
            matched_routes.extend(self._path_methods_from_api_route_call(decorator))

        if not matched_routes:
            return []

        results: list[RouteInfo] = []
        for method, path in matched_routes:
            normalized_path, path_params = self._extract_path_parameters(path)
            results.append(
                RouteInfo(
                    path=normalized_path,
                    method=method,
                    operation_id=func_node.name,
                    function=func_node.name,
                    path_params=path_params,
                )
            )
        return results

    @beartype
    def _extract_string_literal(self, node: ast.AST) -> str | None:
        """Extract string literal from AST node (Python 3.8+ uses ast.Constant)."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    @beartype
    def _extract_path_parameters(self, path: str) -> tuple[str, list[dict[str, Any]]]:
        """Extract path parameters from FastAPI route path."""
        path_params: list[dict[str, Any]] = []
        normalized_path = path

        pattern = r"\{([^}:]+)(?::([^}]+))?\}"
        matches = list(re.finditer(pattern, path))

        type_map = {
            "int": "integer",
            "float": "number",
            "str": "string",
            "uuid": "string",
            "path": "string",
        }

        for match in matches:
            param_name = match.group(1)
            param_type_hint = match.group(2) if match.group(2) else "str"
            openapi_type = type_map.get(param_type_hint.lower(), "string")

            path_params.append(
                {
                    "name": param_name,
                    "in": "path",
                    "required": True,
                    "schema": {"type": openapi_type},
                }
            )

        return normalized_path, path_params
