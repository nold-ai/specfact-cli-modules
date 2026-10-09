"""Actual pinned CLI counterexamples cover every declared Literal input."""

import subprocess
import sys
from pathlib import Path

import pytest

from specfact_code_review.run import target_bootstrap


@pytest.fixture
def literal_cli(tmp_path):
    def check(annotation, condition, *, constructor=False):
        source = tmp_path / "literal_subject.py"
        argument = "options: Options" if constructor else f"value: {annotation}"
        result = "options.value" if constructor else "value"
        subject = (
            "from typing import Literal\nfrom enum import Enum\nfrom dataclasses import dataclass\n"
            "class Marker(Enum):\n    ONE = 1\n"
        )
        if constructor:
            subject += f"@dataclass\nclass Options:\n    value: {annotation}\n"
        source.write_text(
            subject + f'def selected({argument}):\n    """\n    post: {condition}\n    """\n    return {result}\n'
        )
        adapter = Path(target_bootstrap.__file__).with_name("target_crosshair.py")
        return subprocess.run(
            [sys.executable, "-B", str(adapter), "check", "--per_path_timeout", "2", str(source)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    return check


_REVIEW_MODES = 'Literal["full", "changed", "shadow"]'


@pytest.mark.parametrize(
    "annotation,value,constructor",
    [
        (_REVIEW_MODES, "full", False),
        (_REVIEW_MODES, "changed", False),
        (_REVIEW_MODES, "shadow", False),
        (_REVIEW_MODES, "full", True),
        (_REVIEW_MODES, "changed", True),
        (_REVIEW_MODES, "shadow", True),
        (_REVIEW_MODES + " | None", "shadow", False),
        ('Literal["only"]', "only", False),
    ],
)
def test_each_literal_input_has_a_real_counterexample(literal_cli, annotation, value, constructor):
    result = literal_cli(annotation, f"_ != {value!r}", constructor=constructor)
    assert result.returncode == 1 and "false when calling selected" in result.stdout
    assert repr(value) in result.stdout
    assert "TypeError" not in result.stderr


@pytest.mark.parametrize(
    "condition",
    [
        "not (type(_) is bool and _ is False)",
        "not (type(_) is int and _ == 0)",
        "not (type(_) is bool and _ is True)",
        "not (type(_) is int and _ == 1)",
        "_ is not None",
        "_ is not Marker.ONE",
    ],
)
def test_literal_values_preserve_types_and_identity(literal_cli, condition):
    result = literal_cli("Literal[False, 0, True, 1, None, Marker.ONE]", condition)
    assert result.returncode == 1 and "false when calling selected" in result.stdout
    assert "TypeError" not in result.stderr


def test_literal_domain_has_no_undeclared_values(literal_cli):
    result = literal_cli('Literal["full", "changed", "shadow"]', '_ in ("full", "changed", "shadow")')
    assert result.returncode == 0 and result.stdout == "" and result.stderr == ""


def test_non_literal_integer_generation_retains_counterexamples(literal_cli):
    result = literal_cli("int", "_ >= 0")
    assert result.returncode == 1 and "false when calling selected" in result.stdout
    assert "TypeError" not in result.stderr
