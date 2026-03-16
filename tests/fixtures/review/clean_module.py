from __future__ import annotations

from icontract import ensure, require


@require(lambda value: value >= 0, "value must be non-negative")
@ensure(lambda result: result >= 0, "result must be non-negative")
def normalize_value(value: int) -> int:
    return value + 1
