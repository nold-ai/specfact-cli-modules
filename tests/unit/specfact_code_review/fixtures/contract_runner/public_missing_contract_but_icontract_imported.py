"""Fixture parsed by contract_runner tests: ``icontract`` is imported but public API has no contracts."""

import icontract


# Bind so static analyzers treat the import as used; runners only ``ast.parse`` this file.
__fixture_icontract_ref = icontract


def public_without_contracts(value: int) -> int:
    return value + 1
