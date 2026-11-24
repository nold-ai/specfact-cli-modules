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


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param(
            dedent("""\
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
        """),
            ["certain = certain + part"],
            id="prior-writes",
        ),
        pytest.param(
            dedent("""\
        def render(parts, mixed):
            changed = ""
            uncertain = ""
            unchanged = ""
            for part in parts:
                changed = []
                if mixed:
                    uncertain = []
                unchanged = "prefix"
                changed = changed + part
                uncertain = uncertain + part
                unchanged = unchanged + part
        """),
            ["unchanged = unchanged + part"],
            id="loop-body-writes",
        ),
        pytest.param(
            dedent("""\
        def render(parts, mixed):
            uncertain = ""
            certain = ""
            if mixed:
                uncertain = []
            for part in parts:
                if part:
                    uncertain = uncertain + part
                    certain = certain + part
        """),
            ["certain = certain + part"],
            id="conditional-addition",
        ),
        pytest.param(
            dedent("""\
        def render(groups):
            result = ""
            for group in groups:
                for part in group:
                    if part:
                        result = result + part
        """),
            ["result = result + part"],
            id="nested-loop-owner",
        ),
        pytest.param(
            dedent("""\
        result = ""
        for part in [[], [1]]:
            if part:
                result = result + part
            result = []
        """),
            [],
            id="loop-carried-list",
        ),
        pytest.param(
            dedent("""\
        result = ""
        for group in [[], [[1]]]:
            for part in group:
                if part:
                    result = result + part
            result = []
        """),
            [],
            id="outer-loop-carried-list",
        ),
        pytest.param(
            dedent("""\
        result = []
        for part in ("a", "b"):
            result = ""
            if part:
                result = result + part
            result = []
        """),
            ["result = result + part"],
            id="each-iteration-establishes-string",
        ),
        pytest.param(
            dedent("""\
        result = ""
        for part in [[], [1]]:
            if part:
                result = result + part
                result = ""
            else:
                result = []
                continue
            result = ""
        """),
            [],
            id="continue-carries-list",
        ),
    ],
)
def test_concatenation_requires_a_definite_string(tmp_path: Path, source: str, expected: list[str]) -> None:
    findings = feature_patterns(ast.parse(source), tmp_path / "render.py")

    assert [
        source.splitlines()[item["start"]["line"] - 1].strip()
        for item in findings
        if item["check_id"] == "string-concatenation-loop"
    ] == expected


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


def test_new_functions_shadow_imported_callables(tmp_path: Path) -> None:
    source = dedent("""\
        from pickle import loads as unpack
        from pickle import loads as parse_async

        unpack(before)

        def unpack(value):
            return value

        async def parse_async(value):
            return value

        unpack(after)
        parse_async(after)
        """)

    findings = feature_patterns(ast.parse(source), tmp_path / "readers.py")

    assert [
        source.splitlines()[item["start"]["line"] - 1]
        for item in findings
        if item["check_id"] == "unsafe-pickle-deserialization"
    ] == ["unpack(before)"]


@pytest.mark.parametrize("signature", ["decode, /", "decode", "*decode", "*, decode", "**decode"])
def test_function_parameters_shadow_imported_callables(tmp_path: Path, signature: str) -> None:
    source = dedent(f"""\
        from pickle import loads as decode

        def external():
            return decode(value)

        class Reader:
            def external(self):
                return decode(value)

            def local(self, {signature}):
                return decode(value)
        """)

    findings = feature_patterns(ast.parse(source), tmp_path / "readers.py")

    assert [item["start"]["line"] for item in findings if item["check_id"] == "unsafe-pickle-deserialization"] == [4, 8]


def test_parameters_do_not_shadow_enclosing_defaults(tmp_path: Path) -> None:
    source = dedent("""\
        from pickle import loads as decode

        def reader(decode=decode(default)):
            return decode(value)
        """)

    findings = feature_patterns(ast.parse(source), tmp_path / "readers.py")

    assert [item["start"]["line"] for item in findings if item["check_id"] == "unsafe-pickle-deserialization"] == [3]
