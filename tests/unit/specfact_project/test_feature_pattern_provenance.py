"""Verify the source bindings behind Project feature evidence."""

import ast
from pathlib import Path
from textwrap import dedent

import pytest

from specfact_project.analyzers.code_analyzer import CodeAnalyzer
from specfact_project.analyzers.python_patterns import feature_patterns


def test_nested_private_class_does_not_change_outer_feature(tmp_path: Path) -> None:
    path = tmp_path / "services.py"
    source = """\
class Outer:
    def render(self, value=""):
        return value
"""
    path.write_text(source, encoding="utf-8")
    baseline = CodeAnalyzer(tmp_path, confidence_threshold=0.0).analyze().features[0]
    path.write_text(
        source + "\n    class _Helper:\n        def collect(self, items=[]):\n            return items\n",
        encoding="utf-8",
    )

    features = CodeAnalyzer(tmp_path, confidence_threshold=0.0).analyze().features

    assert len(features) == 1
    assert features[0].confidence == baseline.confidence
    assert features[0].constraints == baseline.constraints


def test_route_and_mutable_default_adjust_confidence_independently(tmp_path: Path) -> None:
    path = tmp_path / "services.py"
    template = """\
from fastapi import APIRouter

router = APIRouter()

class WidgetService:
{decorator}    def create_widget(self, names={default}):
        return names
"""

    def confidence(decorator: str = "", default: str = "()") -> float:
        path.write_text(template.format(decorator=decorator, default=default), encoding="utf-8")
        result = CodeAnalyzer(tmp_path, confidence_threshold=0.0).analyze().features[0].confidence
        assert result is not None
        return result

    baseline = confidence()

    assert confidence(decorator='    @router.post("/widgets")\n') == pytest.approx(baseline + 0.1)
    assert confidence(default="[]") == pytest.approx(baseline - 0.05)


def test_only_recognized_sqlalchemy_bases_create_model_evidence(tmp_path: Path) -> None:
    source = dedent("""\
        from sqlalchemy.orm import DeclarativeBase, declarative_base

        class Base:
            pass

        class CsvWriter(Base):
            pass

        class Imported(DeclarativeBase):
            pass

        class Subclass(Imported):
            pass

        OrmBase = declarative_base()

        class Factory(OrmBase):
            pass
        """)

    findings = feature_patterns(ast.parse(source), tmp_path / "models.py")

    assert {
        item["extra"]["metadata"]["model"] for item in findings if item["check_id"] == "sqlalchemy-model-detection"
    } == {
        "Imported",
        "Subclass",
        "Factory",
    }


def test_fastapi_security_dependency_instances_keep_auth_evidence(tmp_path: Path) -> None:
    source = dedent("""\
        from fastapi import APIRouter, Depends, Security
        from fastapi.security import OAuth2PasswordBearer

        api = APIRouter()
        scheme = OAuth2PasswordBearer(tokenUrl="/token")
        metrics = make_recorder()

        @api.get("/protected")
        def protected(user=Depends(scheme)):
            pass

        @api.get("/scoped", dependencies=[Security(scheme)])
        def scoped():
            pass

        @api.get("/health", dependencies=[Depends(metrics)])
        def health():
            pass
        """)

    findings = feature_patterns(ast.parse(source), tmp_path / "routes.py")

    assert [
        source.splitlines()[item["start"]["line"] - 1]
        for item in findings
        if item["check_id"] == "fastapi-dependency-auth-detection"
    ] == ['@api.get("/protected")', '@api.get("/scoped", dependencies=[Security(scheme)])']


def test_ambiguous_prior_writes_do_not_establish_string_accumulators(tmp_path: Path) -> None:
    source = dedent("""\
        def render(parts, mixed):
            uncertain = 0
            certain = 0
            certain = ""
            if mixed:
                uncertain = ""
                certain = "prefix"
                optional = ""
            for part in parts:
                uncertain = uncertain + part
                certain = certain + part
                optional = optional + part
        """)

    findings = feature_patterns(ast.parse(source), tmp_path / "render.py")

    assert [
        source.splitlines()[item["start"]["line"] - 1].strip()
        for item in findings
        if item["check_id"] == "string-concatenation-loop"
    ] == ["certain = certain + part"]


@pytest.mark.parametrize("rebind", ["", "\nfrom pathlib import Path as Router\n"])
def test_route_constructor_keeps_the_import_at_its_assignment(tmp_path: Path, rebind: str) -> None:
    source = (
        dedent("""\
        from fastapi import APIRouter as Router

        api = Router()

        class WidgetService:
            @api.get("/widgets")
            def widgets(self):
                pass

            @Router.get("/unbound")
            def unbound(self):
                pass
        """)
        + rebind
    )

    findings = feature_patterns(ast.parse(source), tmp_path / "routes.py")

    assert [item["extra"]["metadata"] for item in findings if item["check_id"] == "fastapi-route-detection"] == [
        {"method": "GET", "path": "/widgets"}
    ]
