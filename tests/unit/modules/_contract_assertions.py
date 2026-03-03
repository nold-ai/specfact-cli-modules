from __future__ import annotations

import importlib
import inspect


REQUIRED_METHODS = [
    "import_to_bundle",
    "export_from_bundle",
    "sync_with_bundle",
    "validate_bundle",
]


def assert_module_protocol(module_path: str) -> None:
    module = importlib.import_module(module_path)
    for method_name in REQUIRED_METHODS:
        assert hasattr(module, method_name), f"{module_path} missing {method_name}"


def assert_import_signature(module_path: str) -> None:
    module = importlib.import_module(module_path)
    signature = inspect.signature(module.import_to_bundle)
    assert set(signature.parameters.keys()) == {"source", "config"}


def assert_export_signature(module_path: str) -> None:
    module = importlib.import_module(module_path)
    signature = inspect.signature(module.export_from_bundle)
    assert set(signature.parameters.keys()) == {"bundle", "target", "config"}


def assert_contract_wrappers(module_path: str) -> None:
    module = importlib.import_module(module_path)
    for method_name in REQUIRED_METHODS:
        method = getattr(module, method_name)
        assert hasattr(method, "__wrapped__")
        assert hasattr(method, "__preconditions__")
        assert hasattr(method, "__postconditions__")
