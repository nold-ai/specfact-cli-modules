from icontract import ensure, require


@require(lambda value: value >= 0)
@ensure(lambda result: result >= 0)
def public_with_contracts(value: int) -> int:
    return value + 1
