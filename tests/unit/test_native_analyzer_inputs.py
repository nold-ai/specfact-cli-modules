"""Keep experimental native analyzer closures complete, pinned and policy-compatible."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


INPUTS = Path(__file__).parents[2] / "scripts/native_analyzer_inputs"


def requirements(path: Path) -> dict[str, str]:
    """Read logical pip requirement records without annotations."""
    lines = [line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines()]
    content = "\n".join(line for line in lines if line.strip()).replace("\\\n", " ")
    return {
        canonicalize_name(Requirement(line.split("--hash", 1)[0].strip()).name): line for line in content.splitlines()
    }


@pytest.mark.parametrize("abi", ["311", "312", "313"])
def test_hashed_native_closure(abi):
    """Every resolved component has an exact identity, including downstream Z3."""
    pins = requirements(INPUTS / "requirements.in")
    locked = requirements(INPUTS / f"darwin-arm64-cp{abi}.txt")
    assert pins.keys() <= locked.keys()
    assert not {"basedpyright", "nodejs-wheel-binaries"} & locked.keys()
    for name, record in locked.items():
        requirement = Requirement(record.split("--hash", 1)[0].strip())
        assert not requirement.url
        assert not requirement.marker
        assert len(requirement.specifier) == 1
        assert next(iter(requirement.specifier)).operator == "=="
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})(?=\s|$)", record)
        assert hashes, name
        if name in pins:
            assert requirement.specifier == Requirement(pins[name]).specifier
    assert "03eb2624d4d19d06020e9a6c5823cf8ac4f6b3fcb0a73e25ef2514d1129982bd" in locked["z3-solver"]


def test_candidate_policy_floors_and_analyzer_baseline():
    """Retain baseline tools while explicitly advancing the security-floor pair."""
    pins = requirements(INPUTS / "requirements.in")
    expected = {
        "ruff": "0.15.12",
        "radon": "6.0.1",
        "semgrep": "1.175.0",
        "mcp": "1.29.0",
        "pylint": "4.0.7",
        "crosshair-tool": "0.0.109",
        "icontract": "2.7.1",
        "z3-solver": "5.1.0.0+specfact.2",
        "pytest": "9.0.3",
        "pytest-cov": "7.1.0",
        "coverage": "7.15.4",
    }
    for name, version in expected.items():
        assert str(Requirement(pins[name]).specifier) == f"=={version}"
