from __future__ import annotations

import importlib
import inspect

import pytest


REQUIRED_METHODS = [
    "import_to_bundle",
    "export_from_bundle",
    "sync_with_bundle",
    "validate_bundle",
]

MODULES = [
    "specfact_project.plan.commands",
    "specfact_project.sync.commands",
    "specfact_backlog.backlog.commands",
    "specfact_spec.generate.commands",
    "specfact_govern.enforce.commands",
]


@pytest.mark.contract
@pytest.mark.parametrize("module_path", MODULES)
def test_module_implements_protocol(module_path: str) -> None:
    module = importlib.import_module(module_path)
    for method_name in REQUIRED_METHODS:
        assert hasattr(module, method_name), f"{module_path} missing {method_name}"


@pytest.mark.contract
@pytest.mark.parametrize("module_path", MODULES)
def test_import_to_bundle_signature(module_path: str) -> None:
    module = importlib.import_module(module_path)
    signature = inspect.signature(module.import_to_bundle)
    assert set(signature.parameters.keys()) == {"source", "config"}


@pytest.mark.contract
@pytest.mark.parametrize("module_path", MODULES)
def test_export_from_bundle_signature(module_path: str) -> None:
    module = importlib.import_module(module_path)
    signature = inspect.signature(module.export_from_bundle)
    assert set(signature.parameters.keys()) == {"bundle", "target", "config"}


@pytest.mark.contract
@pytest.mark.parametrize("module_path", MODULES)
def test_methods_have_contracts(module_path: str) -> None:
    module = importlib.import_module(module_path)
    for method_name in REQUIRED_METHODS:
        method = getattr(module, method_name)
        assert hasattr(method, "__wrapped__")
        assert hasattr(method, "__preconditions__")
        assert hasattr(method, "__postconditions__")
