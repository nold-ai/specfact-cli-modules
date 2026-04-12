"""Tests for tools/contract_first_smart_test.py (status / relevance helpers)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_contract_first_module():
    path = REPO_ROOT / "tools" / "contract_first_smart_test.py"
    spec = importlib.util.spec_from_file_location("_contract_first_smart_test_mod", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(REPO_ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "tools"))
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def cfst_mod():
    return _load_contract_first_module()


def test_names_require_contract_test_detects_relevant_paths(cfst_mod) -> None:
    assert cfst_mod._names_require_contract_test(["tests/unit/test_x.py"]) is True
    assert cfst_mod._names_require_contract_test(["packages/specfact-backlog/src/x.py"]) is True
    assert cfst_mod._names_require_contract_test(["src/specfact_cli_modules/x.py"]) is True
    assert cfst_mod._names_require_contract_test(["tools/foo.py"]) is True
    assert cfst_mod._names_require_contract_test(["openspec/changes/x/tasks.md"]) is True
    assert cfst_mod._names_require_contract_test(["registry/index.json"]) is True
    assert cfst_mod._names_require_contract_test(["pyproject.toml"]) is True
    assert cfst_mod._names_require_contract_test(["scripts/verify-modules-signature.py"]) is True
    assert cfst_mod._names_require_contract_test(["docs/README.md"]) is False
    assert cfst_mod._names_require_contract_test([".pre-commit-config.yaml"]) is False


def test_contract_test_status_returns_one_when_git_fails(monkeypatch: pytest.MonkeyPatch, cfst_mod) -> None:
    monkeypatch.setattr(
        cfst_mod,
        "_git_staged_names",
        lambda _root: None,
    )
    assert cfst_mod._contract_test_status() == 1


def test_contract_test_status_returns_zero_when_only_irrelevant_staged(
    monkeypatch: pytest.MonkeyPatch, cfst_mod
) -> None:
    monkeypatch.setattr(
        cfst_mod,
        "_git_staged_names",
        lambda _root: ["docs/README.md"],
    )
    assert cfst_mod._contract_test_status() == 0
