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


_FASTAPI_HTTP_VERBS: frozenset[str] = frozenset({"get", "post", "put", "delete", "patch", "head", "options"})


class FastAPIExtractor(BaseFrameworkExtractor):
    """FastAPI framework extractor."""

    @beartype
    @require(lambda repo_path: repo_path.exists(), "Repository path must exist")
    @require(lambda repo_path: repo_path.is_dir(), "Repository path must be a directory")
    @ensure(lambda result: isinstance(result, bool), "Must return bool")
    def detect(self, repo_path: Path) -> bool:
        """
        Detect if FastAPI is used in the repository.

        Args:
            repo_path: Path to repository root

        Returns:
            True if FastAPI is detected
        """
        for candidate_file in ["main.py", "app.py"]:
            file_path = repo_path / candidate_file
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if "from fastapi import" in content or "FastAPI(" in content:
                        return True
                except (UnicodeDecodeError, PermissionError):
                    continue

        # Check in common locations
        for search_path in [repo_path, repo_path / "src", repo_path / "app", repo_path / "backend" / "app"]:
            if not search_path.exists():
                continue
            for py_file in self._iter_python_files(search_path):
                if py_file.name in ["main.py", "app.py"]:
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        if "from fastapi import" in content or "FastAPI(" in content:
                            return True
                    except (UnicodeDecodeError, PermissionError):
                        continue

        return False

    @beartype
    @require(lambda repo_path: repo_path.exists(), "Repository path must exist")
    @require(lambda repo_path: repo_path.is_dir(), "Repository path must be a directory")
    @ensure(lambda result: isinstance(result, list), "Must return list")
    def extract_routes(self, repo_path: Path) -> list[RouteInfo]:
        """
        Extract routes from FastAPI route files.

        Args:
            repo_path: Path to repository root

        Returns:
            List of RouteInfo objects
        """
        results: list[RouteInfo] = []

        # Find FastAPI app files
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
        Extract schemas from Pydantic models for routes.

        Args:
            repo_path: Path to repository root
            routes: List of extracted routes

        Returns:
            Dictionary mapping route identifiers to schema dictionaries
        """
        # Simplified schema extraction - full implementation would parse Pydantic models
        # For now, return empty dict - can be enhanced later
        return {}

    @beartype
    def _extract_routes_from_file(self, py_file: Path) -> list[RouteInfo]:
        """Extract routes from a Python file."""
        try:
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError, PermissionError):
            return []

        imports = self._extract_imports(tree)
        results: list[RouteInfo] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                route_info = self._extract_route_from_function(node, imports, py_file)
                if route_info:
                    results.append(route_info)

        return results

    @beartype
    def _extract_imports(self, tree: ast.AST) -> dict[str, str]:
        """Extract import statements from AST."""
        imports: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    alias_name = alias.asname or alias.name
                    imports[alias_name] = f"{module}.{alias.name}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    alias_name = alias.asname or alias.name
                    imports[alias_name] = alias.name
        return imports

    @beartype
    def _route_path_from_decorator_call(self, call: ast.Call) -> str | None:
        if call.args:
            lit = self._extract_string_literal(call.args[0])
            if lit:
                return lit
        for keyword in call.keywords:
            if keyword.arg in ("path", "route") and keyword.value is not None:
                lit = self._extract_string_literal(keyword.value)
                if lit:
                    return lit
        return None

    @beartype
    def _http_methods_from_api_route_keywords(self, call: ast.Call) -> list[str]:
        for keyword in call.keywords:
            if keyword.arg != "methods" or keyword.value is None:
                continue
            node = keyword.value
            if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
                return []
            methods: list[str] = []
            for element in node.elts:
                raw = self._extract_string_literal(element)
                if raw is None:
                    continue
                lowered = raw.lower()
                if lowered in _FASTAPI_HTTP_VERBS:
                    methods.append(lowered.upper())
            return methods
        return []

    @beartype
    def _decorator_route_name(self, decorator: ast.expr) -> str | None:
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            return decorator.func.attr.lower()
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
            return decorator.func.id.lower()
        return None

    @beartype
    def _path_method_from_route_decorator(self, decorator: ast.expr, path: str, method: str) -> tuple[str, str]:
        if not isinstance(decorator, ast.Call):
            return path, method
        name = self._decorator_route_name(decorator)
        if name is None:
            return path, method

        if name == "api_route":
            extracted_path = self._route_path_from_decorator_call(decorator)
            if extracted_path is not None:
                path = extracted_path
            methods = self._http_methods_from_api_route_keywords(decorator)
            if methods:
                method = methods[0]
            return path, method

        if name in _FASTAPI_HTTP_VERBS:
            extracted_path = self._route_path_from_decorator_call(decorator)
            if extracted_path is not None:
                path = extracted_path
            return path, name.upper()

        return path, method

    @beartype
    def _extract_route_from_function(
        self, func_node: ast.FunctionDef, imports: dict[str, str], py_file: Path
    ) -> RouteInfo | None:
        """Extract route information from a function with FastAPI decorators."""
        path = "/"
        method = "GET"
        operation_id = func_node.name

        for decorator in func_node.decorator_list:
            path, method = self._path_method_from_route_decorator(decorator, path, method)

        normalized_path, path_params = self._extract_path_parameters(path)

        return RouteInfo(
            path=normalized_path,
            method=method,
            operation_id=operation_id,
            function=func_node.name,
            path_params=path_params,
        )

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

        # FastAPI path parameter pattern: {param_name} or {param_name:type}
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
