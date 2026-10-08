"""Restore caller contracts after parent-process CrossHair initialization."""

import importlib

import pytest


@pytest.fixture(autouse=True)
def preserve_caller_icontract_checkers(monkeypatch):
    checker_module = importlib.import_module("icontract._checkers")
    for name in ("_assert_invariant", "_assert_preconditions", "_assert_postconditions"):
        monkeypatch.setattr(checker_module, name, getattr(checker_module, name))
