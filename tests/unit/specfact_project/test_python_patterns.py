"""Verify normalized Python feature and quality evidence."""

import ast
from pathlib import Path
from textwrap import dedent

from specfact_project.analyzers.python_patterns import feature_patterns


def test_routes_keep_http_methods_and_attach_only_auth_dependencies(tmp_path: Path) -> None:
    source = dedent("""\
        from fastapi import Depends, Security

        @app.get("/health", dependencies=[Depends(record_metrics)])
        def health():
            pass

        @app.get("/protected", dependencies=[Depends(dependency=require_auth)])
        def protected():
            pass

        @app.get("/scoped", dependencies=[Security(check_scopes)])
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
    assert [item["start"]["line"] for item in findings if item["check_id"] == "fastapi-dependency-auth-detection"] == [
        7,
        11,
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
