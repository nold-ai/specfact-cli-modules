from __future__ import annotations


# pylint: disable=bare-except


def risky_transform(value: int) -> int:
    total = 0
    if value > 0:
        total += 1
    if value > 1:
        total += 1
    if value > 2:
        total += 1
    if value > 3:
        total += 1
    if value > 4:
        total += 1
    if value > 5:
        total += 1
    if value > 6:
        total += 1
    if value > 7:
        total += 1
    if value > 8:
        total += 1
    if value > 9:
        total += 1
    if value > 10:
        total += 1
    if value > 11:
        total += 1
    if value > 12:
        total += 1
    if value > 13:
        total += 1
    if value > 14:
        total += 1
    try:
        print(total)
    except:  # noqa: E722
        return -1
    return total
