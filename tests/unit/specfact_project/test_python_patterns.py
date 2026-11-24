"""Verify normalized Python feature and quality evidence."""

import ast
from pathlib import Path
from textwrap import dedent

from specfact_project.analyzers.python_patterns import feature_patterns


def test_routes_keep_http_methods_and_attach_only_auth_dependencies(tmp_path: Path) -> None:
    source = dedent("""\
        from fastapi import APIRouter, Depends, Security
        from flask import Blueprint

        api = APIRouter()
        app = Blueprint("widgets", __name__)

        @api.get("/health", dependencies=[Depends(record_metrics)])
        def health():
            pass

        @api.get("/protected", dependencies=[Depends(dependency=require_auth)])
        def protected():
            pass

        @api.get("/scoped", dependencies=[Security(require_permission)])
        def scoped():
            pass

        @app.route("/widgets", methods=["POST", "PATCH", "UNKNOWN"])
        def widgets():
            pass

        @app.route("/default")
        def index():
            pass
        """)
    path = tmp_path / "routes.py"

    findings = feature_patterns(ast.parse(source), path)

    assert {item["path"] for item in findings} == {str(path)}
    auth = [item["start"]["line"] for item in findings if item["check_id"] == "fastapi-dependency-auth-detection"]
    assert [source.splitlines()[line - 1] for line in auth] == [
        '@api.get("/protected", dependencies=[Depends(dependency=require_auth)])',
        '@api.get("/scoped", dependencies=[Security(require_permission)])',
    ]
    assert [item["extra"]["metadata"] for item in findings if item["check_id"] == "flask-route-detection"] == [
        {"method": "POST", "path": "/widgets"},
        {"method": "PATCH", "path": "/widgets"},
        {"method": "GET", "path": "/default"},
    ]


def test_reports_scoped_python_quality_and_feature_signals(tmp_path: Path) -> None:
    source = dedent("""\
        import logging as log
        import os
        import optparse
        import structlog
        from dataclasses import dataclass
        from pydantic_settings import BaseSettings

        __all__ = ["render"]
        logger = log.getLogger(__name__)
        label = os.environ["LABEL"]
        labels = [item for item in items]
        generated = (item for item in items)
        converter = lambda value: str(value)

        class Config(BaseSettings):
            name: str = "widgets"

        class WidgetException(Exception):
            pass

        @dataclass
        class Widget:
            name: str

        class WidgetRepository(Repository):
            def __init__(self):
                pass

        def render(parts):
            output = ""
            try:
                for part in parts:
                    output = output + part
                    count = len(output)
                    copy = output + part
            except:
                return ""
            finally:
                logger.info("rendered")
            return output
        """)
    findings = feature_patterns(ast.parse(source), tmp_path / "widgets.py")
    by_rule = {item["check_id"]: item for item in findings}

    assert {
        "bare-except-antipattern",
        "custom-exception-class",
        "dataclass-usage",
        "deprecated-optparse-module",
        "env-variable-access",
        "finally-block-usage",
        "generator-expression",
        "lambda-assignment-antipattern",
        "list-comprehension-usage",
        "logger-instantiation",
        "pydantic-settings-detection",
        "repository-pattern-detection",
        "structlog-usage",
    } <= by_rule.keys()
    concatenations = [item["start"]["line"] for item in findings if item["check_id"] == "string-concatenation-loop"]
    assert len(concatenations) == 1
    assert source.splitlines()[concatenations[0] - 1].strip() == "output = output + part"


def test_only_known_http_receivers_produce_route_findings(tmp_path: Path) -> None:
    source = dedent("""\
        from fastapi import APIRouter
        from flask import Flask

        api = APIRouter()
        app = Flask(__name__)
        methods = ["POST"]

        @api.get(path="/widgets")
        def widgets():
            pass

        @cache.get("/internal")
        def cached():
            pass

        @app.route("/explicit", methods=methods)
        def unresolved():
            pass

        @app.post("/orders")
        def orders():
            pass
        """)
    findings = feature_patterns(ast.parse(source), tmp_path / "routes.py")

    routes = {
        (item["check_id"], item["extra"]["metadata"]["method"], item["extra"]["metadata"]["path"])
        for item in findings
        if item["check_id"].endswith("-route-detection")
    }
    assert routes == {
        ("fastapi-route-detection", "GET", "/widgets"),
        ("flask-route-detection", "POST", "/orders"),
    }


def test_route_authentication_requires_known_dependencies(tmp_path: Path) -> None:
    source = dedent("""\
        from fastapi import APIRouter, Depends, Security
        from typing import Annotated

        api = APIRouter()

        @api.get("/health", dependencies=[Security(record_metrics)])
        def health():
            pass

        @api.get("/auth")
        def authenticated(user=Depends(get_current_user)):
            pass

        @api.get("/scoped")
        def scoped(user: Annotated[str, Security(require_permission, scopes=["read"])]):
            pass

        @api.get("/anonymous", dependencies=[Depends(record_metrics)])
        def anonymous():
            pass
        """)
    findings = feature_patterns(ast.parse(source), tmp_path / "authorization.py")

    matches = [item["start"]["line"] for item in findings if item["check_id"] == "fastapi-dependency-auth-detection"]
    assert [source.splitlines()[line - 1] for line in matches] == ['@api.get("/auth")', '@api.get("/scoped")']


def test_local_imports_stay_in_their_own_function(tmp_path: Path) -> None:
    source = dedent("""\
        def first():
            import logging as log
            return log.getLogger("first")

        def second():
            import cache as log
            return log.getLogger("second")

        class Reporter:
            import logging as log

            def emit(self):
                return log.getLogger("unbound")
        """)
    findings = feature_patterns(ast.parse(source), tmp_path / "helpers.py")

    lines = [item["start"]["line"] for item in findings if item["check_id"] == "logger-instantiation"]
    assert lines == [3]


def test_numeric_accumulator_is_not_string_evidence(tmp_path: Path) -> None:
    source = dedent("""\
        def summarize(parts):
            text = ""
            total = 0
            for part in parts:
                total = total + len(part)
                text = text + part
            return text, total
        """)
    findings = feature_patterns(ast.parse(source), tmp_path / "formatting.py")

    matches = [item for item in findings if item["check_id"] == "string-concatenation-loop"]
    assert [source.splitlines()[item["start"]["line"] - 1].strip() for item in matches] == ["text = text + part"]
    assert matches[0]["message"] == "Review repeated concatenation in a loop"
