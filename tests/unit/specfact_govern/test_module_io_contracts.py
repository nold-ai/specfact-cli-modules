from __future__ import annotations

import pytest

from tests.unit.modules._contract_assertions import (
    assert_contract_wrappers,
    assert_export_signature,
    assert_import_signature,
    assert_module_protocol,
)


MODULES = ["specfact_govern.enforce.commands"]


@pytest.mark.contract
@pytest.mark.parametrize("module_path", MODULES)
def test_module_implements_protocol(module_path: str) -> None:
    assert_module_protocol(module_path)


@pytest.mark.contract
@pytest.mark.parametrize("module_path", MODULES)
def test_import_to_bundle_signature(module_path: str) -> None:
    assert_import_signature(module_path)


@pytest.mark.contract
@pytest.mark.parametrize("module_path", MODULES)
def test_export_from_bundle_signature(module_path: str) -> None:
    assert_export_signature(module_path)


@pytest.mark.contract
@pytest.mark.parametrize("module_path", MODULES)
def test_methods_have_contracts(module_path: str) -> None:
    assert_contract_wrappers(module_path)
